"""Analysis mixin: reports, metacognition and learning advice."""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from itertools import combinations

from .reasoning import suggested_pack_size
from .types import (
    MemoryItem,
    MemoryKind,
    RecallResult,
    tokenize,
    utcnow,
)
from .zh_nlp import expand_synonyms


class AnalysisMixin:
    def memory_health(self) -> dict:
        """Return one overall memory-health score with sub-metrics.

        Metacognitive monitoring (Koriat & Goldsmith, 1996): a memory
        system should know how healthy it is. This aggregates existing
        read-only signals - linked ratio, crowded cues, conflicts,
        overdue/clashing intentions and suppressed memories - into a
        0-100 score with itemized penalties.
        """
        active = self.store.all_active()
        memory_count = len(active)
        assoc = self.association_report(limit=5)
        connected = assoc["connected_count"]
        linked_ratio = (
            round(connected / memory_count, 3) if memory_count else 0.0
        )
        crowded = len(
            self.interference_report(shared_cue_min=3)["crowded_clusters"]
        )
        conflicts = len(self.consolidator.detect_conflicts())
        intents = self.intent_report()
        clashes = self.intent_conflicts()["total"]
        suppressed = self.suppressed_report()["count"]
        penalties = {
            "isolated": min(
                20, round((1.0 - linked_ratio) * 50)
            ),
            "crowded": min(15, crowded * 3),
            "conflicts": min(20, conflicts * 4),
            "overdue_intents": min(10, intents["overdue"] * 2),
            "intent_clashes": min(10, clashes * 3),
            "suppressed": min(5, suppressed),
        }
        score = max(0, 100 - sum(penalties.values()))
        return {
            "score": score,
            "memory_count": memory_count,
            "linked_ratio": linked_ratio,
            "crowded_clusters": crowded,
            "conflicts": conflicts,
            "overdue_intents": intents["overdue"],
            "intent_clashes": clashes,
            "suppressed_count": suppressed,
            "penalties": penalties,
        }

    def memory_map(
        self,
        now: datetime | None = None,
        limit: int = 200,
        topic_min: int = 1,
    ) -> dict:
        """Summarize what the memory holds: topics, time and strength.

        Clusters active memories by their leading cue (or content prefix),
        reports per-topic counts with average retrievability/importance,
        and buckets the whole sample into weak / ok / strong. This is the
        data behind the human-readable memory-map chart.
        """
        now = now or utcnow()
        # Sample only the newest `limit` memories instead of loading the
        # whole store (the default chart is about the recent working set).
        items = self.store.all_active(limit=max(1, int(limit)))
        groups: dict[str, list[MemoryItem]] = {}
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:12]
            groups.setdefault(topic, []).append(item)
        rows: list[dict] = []
        for topic, members in groups.items():
            if len(members) < max(1, int(topic_min)):
                continue
            rows.append(
                {
                    "topic": topic,
                    "count": len(members),
                    "avg_retrievability": round(
                        sum(
                            self.curve.retrievability(member, now)
                            for member in members
                        )
                        / len(members),
                        3,
                    ),
                    "avg_importance": round(
                        sum(member.importance for member in members)
                        / len(members),
                        3,
                    ),
                    "recent": members[0].content[:60],
                }
            )
        rows.sort(key=lambda row: (-row["count"], -row["avg_importance"]))
        strength = {"weak": 0, "ok": 0, "strong": 0}
        for item in items:
            retrievability = self.curve.retrievability(item, now)
            if retrievability < 0.3:
                strength["weak"] += 1
            elif retrievability < 0.7:
                strength["ok"] += 1
            else:
                strength["strong"] += 1
        return {
            "sampled": len(items),
            "topics": rows[: max(1, int(limit))],
            "strength": strength,
            "generated_at": utcnow().isoformat(),
        }

    def kg_export(self) -> dict:
        """Export the memory network as a knowledge-graph edge list.

        Semantic-network organization (Collins & Quillian, 1969): related
        facts form a graph. This returns nodes and deduplicated undirected
        edges so external tools can visualize or analyze the store.
        """
        items = {
            item.id: item for item in self.store.all_active()
        }
        nodes = [
            {
                "id": item.id,
                "label": item.content[:24],
                "kind": item.kind.value,
            }
            for item in items.values()
        ]
        edges = []
        seen: set[frozenset[str]] = set()
        for src, dst, weight in self.backend.all_links():
            if src not in items or dst not in items:
                continue
            pair = frozenset((src, dst))
            if pair in seen:
                continue
            seen.add(pair)
            edges.append(
                {
                    "source": src,
                    "target": dst,
                    "weight": round(float(weight), 3),
                }
            )
        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges),
        }
    def learner_profile(self, now: datetime | None = None) -> dict:
        """Estimate the learner's rate from review history.

        Adaptive spaced repetition estimates learning rate from observed
        retrieval success (Mozer et al., 2009): fast learners get longer
        intervals, struggling ones get shorter ones. This reports the
        estimated profile and a suggested interval scale.
        """
        items = self.store.all_active()
        total_reviews = 0
        successes = 0
        retrievability_sum = 0.0
        importance_sum = 0.0
        for item in items:
            total_reviews += (
                item.retrieval_successes + item.retrieval_failures
            )
            successes += item.retrieval_successes
            retrievability_sum += self.curve.retrievability(item, now)
            importance_sum += item.importance
        n = len(items)
        success_rate = (
            successes / total_reviews if total_reviews else None
        )
        if n == 0 or success_rate is None:
            profile = "unknown"
            scale = 1.0
        elif success_rate >= 0.8:
            profile = "fast"
            scale = 1.2
        elif success_rate >= 0.6:
            profile = "steady"
            scale = 1.0
        else:
            profile = "struggling"
            scale = 0.8
        return {
            "total_memories": n,
            "total_reviews": total_reviews,
            "success_rate": (
                round(success_rate, 3) if success_rate is not None else None
            ),
            "avg_retrievability": round(
                retrievability_sum / max(1, n), 3
            ),
            "avg_importance": round(importance_sum / max(1, n), 3),
            "profile": profile,
            "suggested_interval_scale": scale,
        }
    def context_pack(
        self,
        queries: list[str],
        *,
        top_k: int = 3,
        max_chars: int = 1200,
        now: datetime | None = None,
    ) -> dict:
        """Pack the best matching memories into a bounded context.

        Working memory is limited; cognitive-load theory (Sweller, 1988)
        says only the essential information should reach the model. This
        runs recall for several queries, deduplicates by id, ranks by
        score and returns as much as fits the character budget.
        """
        best: dict[str, tuple[float, str]] = {}
        found = 0
        for query in queries:
            for result in self.recall(query, top_k=top_k, now=now):
                if not any(
                    "overlap" in r
                    or "semantic" in r
                    or r.startswith("概念覆盖")
                    for r in result.reasons
                ):
                    continue
                found += 1
                item = result.item
                current = best.get(item.id)
                if current is None or result.score > current[0]:
                    best[item.id] = (
                        result.score, item.content
                    )
        ranked = sorted(
            best.items(), key=lambda kv: kv[1][0], reverse=True
        )
        packed = []
        used = 0
        truncated = 0
        for memory_id, (score, content) in ranked:
            if used + len(content) > max(1, int(max_chars)) and packed:
                truncated += 1
                continue
            packed.append(
                {
                    "id": memory_id,
                    "content": content,
                    "score": round(score, 3),
                }
            )
            used += len(content)
        return {
            "query_count": len(queries),
            "total_found": found,
            "unique_found": len(best),
            "packed_count": len(packed),
            "packed_chars": used,
            "truncated_count": truncated,
            "packed": packed,
        }
    def encoding_quality(self, memory_id: str) -> dict | None:
        """Score how well one memory was encoded.

        Elaborative encoding (Craik & Tulving, 1975): deeper encoding
        (more cues, context, emotion, importance) makes a memory more
        retrievable. This scores 0-100 and suggests what is missing.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        cue_count = len(item.cues)
        has_context = bool(item.context)
        has_affect = bool(item.affect)
        content_length = len(item.content)
        score = 0.0
        suggestions = []
        if cue_count >= 2:
            score += 25
        elif cue_count == 1:
            score += 15
            suggestions.append("再补 1 个线索（日期/对象/主题）")
        else:
            suggestions.append("没有线索，先加 2 个检索线索")
        if has_context:
            score += 20
        else:
            suggestions.append("缺少情景上下文，补一句当时的环境")
        if has_affect:
            score += 10
        if item.importance >= 0.6:
            score += 15
        elif item.importance >= 0.3:
            score += 10
            suggestions.append("重要度偏低，确认是否值得长期保留")
        if item.strength >= 0.5:
            score += 15
        else:
            suggestions.append("记忆强度偏低，建议尽快复习一次")
        if 10 <= content_length <= 200:
            score += 15
        elif content_length > 200:
            score += 8
            suggestions.append("内容偏长，考虑拆成几条")
        else:
            score += 5
            suggestions.append("内容太短，补充一点细节")
        score = min(100, round(score))
        if score >= 80:
            verdict = "well_encoded"
        elif score >= 60:
            verdict = "adequate"
        else:
            verdict = "weak"
        return {
            "memory_id": memory_id,
            "score": score,
            "verdict": verdict,
            "cue_count": cue_count,
            "has_context": has_context,
            "has_affect": has_affect,
            "importance": round(item.importance, 3),
            "strength": round(item.strength, 3),
            "content_length": content_length,
            "suggestions": suggestions[:4],
        }
    def explain_memory(
        self,
        memory_id: str,
        now: datetime | None = None,
    ) -> dict | None:
        """Explain one memory's full state in plain fields.

        Metacognitive monitoring (Koriat & Goldsmith, 1996): an agent
        should be able to say why a memory exists and how reachable it
        is. This returns content, cues, retrievability, importance,
        strength, confidence, evidence, links, suppression, access and
        review state.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return None
        linked_count = sum(
            1
            for src, dst, _weight in self.backend.all_links()
            if src == memory_id or dst == memory_id
        )
        return {
            "memory_id": memory_id,
            "content": item.content,
            "kind": item.kind.value,
            "created_at": item.created_at.isoformat(),
            "cues": item.cues,
            "retrievability": round(
                self.curve.retrievability(item, now), 3
            ),
            "importance": round(item.importance, 3),
            "strength": round(item.strength, 3),
            "confidence": round(item.confidence, 3),
            "evidence_count": item.evidence_count,
            "linked_count": linked_count,
            "suppressed": memory_id in self._suppressed_ids,
            "access_count": item.access_count,
            "last_access_at": (
                item.last_access_at.isoformat()
                if item.last_access_at is not None
                else None
            ),
            "review_streak": item.review_streak,
            "last_review_at": (
                item.last_review_at.isoformat()
                if item.last_review_at is not None
                else None
            ),
        }
    def compare_memories(self, id_a: str, id_b: str) -> dict | None:
        """Compare two memories: overlap, differences and verdict.

        Source monitoring and schema integration (Johnson, Hashtroudi &
        Lindsay, 1993): agents holding two records of the same event must
        know whether they duplicate, conflict or are simply distinct. This
        reports token overlap, shared cues and a verdict.
        """

        a = self.backend.get(id_a)
        b = self.backend.get(id_b)
        if a is None or b is None:
            return None
        a_terms = set(tokenize(a.content))
        b_terms = set(tokenize(b.content))
        common_terms = sorted(a_terms & b_terms)
        overlap = (
            len(common_terms) / max(1, min(len(a_terms), len(b_terms)))
            if a_terms and b_terms
            else 0.0
        )
        shared_cues = sorted(set(a.cues) & set(b.cues))
        if overlap >= 0.6:
            verdict = "duplicate"
        elif shared_cues and a.content != b.content:
            verdict = "conflict"
        else:
            verdict = "distinct"
        return {
            "a": {
                "id": a.id,
                "preview": a.content[:40],
                "kind": a.kind.value,
                "importance": round(a.importance, 3),
                "confidence": round(a.confidence, 3),
                "evidence_count": a.evidence_count,
                "created_at": a.created_at.isoformat(),
            },
            "b": {
                "id": b.id,
                "preview": b.content[:40],
                "kind": b.kind.value,
                "importance": round(b.importance, 3),
                "confidence": round(b.confidence, 3),
                "evidence_count": b.evidence_count,
                "created_at": b.created_at.isoformat(),
            },
            "overlap": round(overlap, 3),
            "common_terms": common_terms[:5],
            "shared_cues": shared_cues[:5],
            "verdict": verdict,
        }
    def summarize_cluster(
        self,
        memory_ids: list[str],
    ) -> dict | None:
        """Summarize a cluster of related memories as one gist.

        Fuzzy-trace theory (Brainerd & Reyna, 1990): people keep the gist
        of repeated related experiences rather than every verbatim
        detail. This extracts shared cues, frequent terms and evidence
        counts into a compact summary an agent can use (or write back).
        """

        items = []
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is not None:
                items.append(item)
        if not items:
            return None
        cue_sets = [set(item.cues) for item in items]
        common_cues = sorted(set.intersection(*cue_sets)) if cue_sets else []
        term_counter: Counter = Counter()
        for item in items:
            for term in tokenize(item.content):
                term_counter[term] += 1
        top_terms = [
            term for term, _count in term_counter.most_common(6)
        ]
        total_chars = sum(len(item.content) for item in items)
        evidence = sum(item.evidence_count for item in items)
        previews = [item.content[:24] for item in items[:4]]
        summary = (
            f"共 {len(items)} 条记忆，共享线索："
            + ("、".join(common_cues) if common_cues else "无")
            + f"；高频词：{'、'.join(top_terms) if top_terms else '无'}；"
            + f"累计证据 {evidence} 次"
        )
        return {
            "memory_ids": [item.id for item in items],
            "summary": summary,
            "common_cues": common_cues,
            "top_terms": top_terms,
            "evidence_count": evidence,
            "total_chars": total_chars,
            "previews": previews,
        }
    def multi_hop_report(
        self,
        start_id: str,
        depth: int = 2,
        limit: int = 20,
    ) -> dict | None:
        """Walk the association network hop by hop from a start memory.

        Spreading activation (Collins & Loftus, 1975): related memories
        become reachable through their links, hop by hop. This BFS report
        shows which memories appear at each distance, so agents can gather
        multi-hop evidence for reasoning.
        """

        if self.backend.get(start_id) is None:
            return None
        adj: dict[str, set[str]] = defaultdict(set)
        for src, dst, _weight in self.backend.all_links():
            adj[src].add(dst)
            adj[dst].add(src)
        frontier = {start_id}
        seen = {start_id}
        hops = []
        for hop in range(1, max(1, int(depth)) + 1):
            next_frontier: set[str] = set()
            for node in frontier:
                next_frontier |= adj.get(node, set())
            next_frontier -= seen
            if not next_frontier:
                break
            seen |= next_frontier
            hops.append(
                {
                    "hop": hop,
                    "memory_ids": sorted(next_frontier)[: max(1, int(limit))],
                    "count": len(next_frontier),
                }
            )
            frontier = next_frontier
        return {
            "start_id": start_id,
            "depth": max(1, int(depth)),
            "hops": hops,
            "total_reached": len(seen) - 1,
            "reached_ids": sorted(seen - {start_id})[: max(1, int(limit))],
        }
    def cramming_plan(
        self,
        target_at: datetime,
        hours_available: float = 6.0,
        session_minutes: int = 30,
        limit: int = 20,
    ) -> dict:
        """Plan a last-minute review schedule before a deadline.

        Even with little time, spacing beats massing (Cepeda et al.,
        2006): the available hours are split into short sessions and the
        most at-risk important memories are reviewed first.
        """

        scored = []
        for item in self.store.all_active():
            need = item.importance * (
                1.0 - self.curve.retrievability(item, target_at)
            )
            scored.append((need, item))
        scored.sort(key=lambda pair: -pair[0])
        picked = scored[: max(1, int(limit))]
        n_sessions = max(
            1,
            int(float(hours_available) * 60 // max(1, int(session_minutes))),
        )
        per_session = len(picked) // n_sessions
        extra = len(picked) % n_sessions
        sessions = []
        for i in range(n_sessions):
            start = i * per_session + min(i, extra)
            size = per_session + (1 if i < extra else 0)
            chunk = picked[start:start + size]
            if not chunk:
                break
            start = target_at - timedelta(
                minutes=max(1, int(session_minutes)) * (n_sessions - i)
            )
            sessions.append(
                {
                    "start_at": start.isoformat(),
                    "duration_minutes": max(1, int(session_minutes)),
                    "memory_ids": [item.id for _need, item in chunk],
                    "count": len(chunk),
                }
            )
        return {
            "target_at": target_at.isoformat(),
            "hours_available": round(float(hours_available), 2),
            "sessions": sessions,
            "total_memories": len(picked),
        }
    def session_summary(
        self,
        memory_ids: list[str],
        compare_limit: int = 20,
    ) -> dict | None:
        """Summarize one work session's memories into facts/events/issues.

        Post-session consolidation integrates new traces into knowledge:
        this splits the memories into semantic facts and episodic events,
        then flags conflict and duplicate pairs so the agent can resolve
        them before moving on.
        """

        items = []
        for memory_id in memory_ids:
            item = self.backend.get(memory_id)
            if item is not None:
                items.append(item)
        if not items:
            return None
        facts = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items if item.kind is MemoryKind.SEMANTIC
        ]
        events = [
            {"id": item.id, "preview": item.content[:40]}
            for item in items if item.kind is MemoryKind.EPISODIC
        ]
        conflicts = []
        duplicates = []
        compare_items = items[: max(2, int(compare_limit))]
        for a, b in combinations(compare_items, 2):
            verdict = self.compare_memories(a.id, b.id)["verdict"]
            if verdict == "conflict" and len(conflicts) < 5:
                conflicts.append(
                    {"id_a": a.id, "id_b": b.id,
                     "a_preview": a.content[:24],
                     "b_preview": b.content[:24]}
                )
            elif verdict == "duplicate" and len(duplicates) < 5:
                duplicates.append(
                    {"id_a": a.id, "id_b": b.id,
                     "a_preview": a.content[:24],
                     "b_preview": b.content[:24]}
                )
        summary = (
            f"共 {len(items)} 条记忆：事实 {len(facts)} 条、"
            f"事件 {len(events)} 条、冲突 {len(conflicts)} 对、"
            f"重复 {len(duplicates)} 对"
        )
        return {
            "total": len(items),
            "facts": facts,
            "events": events,
            "conflicts": conflicts,
            "duplicates": duplicates,
            "summary": summary,
        }
    def topic_drift_report(
        self,
        period_days: int = 30,
        limit: int = 20,
    ) -> dict:
        """Compare topic distribution between the two most recent periods.

        Schemas are reconstructed and shift over time (Bartlett, 1932):
        this compares the newest time bucket against the previous one and
        reports which themes grew, shrank, appeared or disappeared.
        """
        story = self.life_story(
            period_days=max(1, int(period_days)),
            limit=max(2, int(limit)),
        )
        periods = story["periods"]
        if len(periods) < 2:
            return {
                "periods": [p["period_start"] for p in periods],
                "topics": [],
                "total_drift": 0,
            }
        old, new = periods[-2], periods[-1]
        old_counts = {t["cue"]: t["count"] for t in old["top_themes"]}
        new_counts = {t["cue"]: t["count"] for t in new["top_themes"]}
        all_topics = sorted(set(old_counts) | set(new_counts))
        topics = []
        for topic in all_topics:
            old_count = old_counts.get(topic, 0)
            new_count = new_counts.get(topic, 0)
            delta = new_count - old_count
            if old_count == 0:
                status = "new"
            elif new_count == 0:
                status = "gone"
            elif delta > 0:
                status = "grew"
            elif delta < 0:
                status = "shrank"
            else:
                status = "same"
            topics.append(
                {
                    "topic": topic,
                    "old_count": old_count,
                    "new_count": new_count,
                    "delta": delta,
                    "status": status,
                }
            )
        total_drift = sum(
            1 for t in topics if t["status"] not in ("same",)
        )
        return {
            "periods": [old["period_start"], new["period_start"]],
            "topics": topics,
            "total_drift": total_drift,
        }
    def forgetting_export(
        self,
        memory_id: str,
        days: int = 30,
        step_days: int = 1,
    ) -> dict | None:
        """Export a memory's predicted forgetting curve.

        The forgetting curve (Ebbinghaus, 1885) predicts retrievability
        over time; this returns the forecast at regular intervals so
        agents or dashboards can plot it.
        """

        item = self.backend.get(memory_id)
        if item is None:
            return None
        now = utcnow()
        points = []
        for offset in range(
            0,
            max(1, int(days)) + 1,
            max(1, int(step_days)),
        ):
            points.append(
                {
                    "days_from_now": offset,
                    "retrievability": round(
                        self.curve.retrievability(
                            item, now + timedelta(days=offset)
                        ),
                        3,
                    ),
                }
            )
        return {
            "memory_id": memory_id,
            "content": item.content[:40],
            "initial": points[0]["retrievability"],
            "final": points[-1]["retrievability"],
            "points": points,
        }
    def coverage_report(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Report review coverage per topic schema.

        Spaced-review systems need coverage monitoring: a topic with many
        never-reviewed memories is a blind spot. This reports, per topic,
        memory count, reviewed count, coverage ratio, average
        retrievability/importance and a status.
        """
        schema = self.schema_report(limit=max(1, int(limit)))
        topics = []
        for group in schema["top_groups"]:
            topic = group["topic"]
            members = [
                item
                for item in self.store.all_active()
                if item.cues and item.cues[0] == topic
            ]
            reviewed = [
                item for item in members
                if item.retrieval_successes + item.retrieval_failures > 0
            ]
            count = len(members)
            coverage = round(len(reviewed) / count, 3) if count else 1.0
            if coverage == 0:
                status = "unreviewed"
            elif coverage < 0.5:
                status = "partial"
            else:
                status = "good"
            topics.append(
                {
                    "topic": topic,
                    "memory_count": count,
                    "reviewed_count": len(reviewed),
                    "coverage": coverage,
                    "avg_retrievability": round(
                        sum(
                            self.curve.retrievability(item, now)
                            for item in members
                        ) / max(1, count),
                        3,
                    ),
                    "avg_importance": group["avg_importance"],
                    "status": status,
                }
            )
        return {
            "topics": topics,
            "total_topics": len(topics),
        }
    def source_calibration(self) -> dict:
        """Score the trustworthiness of each memory source.

        Source monitoring (Johnson, Hashtroudi & Lindsay, 1993): agents
        should know which origins are reliable. This groups memories by
        source origin and scores each source from its average confidence,
        evidence and importance.
        """

        groups: dict[str, list] = defaultdict(list)
        for item in self.store.all_active():
            groups[item.source.origin.value].append(item)
        sources = []
        for origin, members in sorted(groups.items()):
            count = len(members)
            avg_confidence = (
                sum(item.confidence for item in members) / count
            )
            avg_evidence = (
                sum(item.evidence_count for item in members) / count
            )
            avg_importance = (
                sum(item.importance for item in members) / count
            )
            avg_trust = sum(item.source.trust for item in members) / count
            trust_score = round(
                0.4 * avg_confidence
                + 0.3 * min(1.0, avg_evidence / 3.0)
                + 0.2 * avg_importance
                + 0.1 * avg_trust,
                3,
            )
            sources.append(
                {
                    "origin": origin,
                    "memory_count": count,
                    "avg_confidence": round(avg_confidence, 3),
                    "avg_evidence": round(avg_evidence, 3),
                    "avg_importance": round(avg_importance, 3),
                    "avg_source_trust": round(avg_trust, 3),
                    "trust_score": trust_score,
                }
            )
        sources.sort(key=lambda s: -s["trust_score"])
        return {
            "sources": sources,
            "total_memories": sum(s["memory_count"] for s in sources),
        }
    def forgetting_risk(
        self,
        now: datetime | None = None,
        limit: int = 20,
    ) -> dict:
        """Rank memories by forgetting risk.

        The riskiest memories are the most important ones closest to
        being forgotten (importance x forgetting); agents should review
        those first.
        """
        scored = []
        for item in self.store.all_active():
            retrievability = self.curve.retrievability(item, now)
            risk = item.importance * (1.0 - retrievability)
            scored.append(
                {
                    "id": item.id,
                    "preview": item.content[:40],
                    "importance": round(item.importance, 3),
                    "retrievability": round(retrievability, 3),
                    "risk": round(risk, 3),
                }
            )
        scored.sort(key=lambda entry: (-entry["risk"], entry["id"]))
        riskiest = scored[: max(1, int(limit))]
        return {
            "total": len(scored),
            "avg_risk": round(
                sum(entry["risk"] for entry in scored) / max(1, len(scored)),
                3,
            ),
            "riskiest": riskiest,
        }
    def bridge_suggestions(
        self,
        limit: int = 20,
    ) -> dict:
        """Suggest missing links between memories sharing cues.

        Spreading activation works through links (Collins & Loftus, 1975):
        memories that share a cue but have no link are a gap in the
        network. This lists those pairs so the agent can add bridges.
        """

        items = self.store.all_active()
        existing: set[frozenset[str]] = set()
        for src, dst, _weight in self.backend.all_links():
            existing.add(frozenset((src, dst)))
        suggestions = []
        compare_items = items[: min(max(2, int(limit) * 3), 200)]
        for a, b in combinations(compare_items, 2):
            if len(suggestions) >= max(1, int(limit)):
                break
            shared = sorted(set(a.cues) & set(b.cues))
            if not shared:
                continue
            if frozenset((a.id, b.id)) in existing:
                continue
            suggestions.append(
                {
                    "id_a": a.id,
                    "id_b": b.id,
                    "a_preview": a.content[:24],
                    "b_preview": b.content[:24],
                    "shared_cues": shared[:4],
                }
            )
        return {
            "total": len(suggestions),
            "suggestions": suggestions,
        }
    def retrieval_quality(
        self,
        queries: list[str] | None = None,
        top_k: int = 5,
        now: datetime | None = None,
        limit: int = 10,
    ) -> dict:
        """Measure retrieval quality across a set of queries.

        Metacognitive monitoring of retrieval (Koriat & Goldsmith, 1996):
        run the real recall pipeline over known queries and report average
        top score, top retrievability, hit rate and weak rate.
        """
        if not queries:
            queries = [
                item.cues[0]
                for item in self.store.all_active()
                if item.cues
            ][: max(1, int(limit))]
        top_scores = []
        top_retrievability = []
        hit_count = 0
        weak_count = 0
        for query in queries:
            results = self.recall(query, top_k=max(1, int(top_k)), now=now)
            if not results:
                weak_count += 1
                continue
            top = results[0]
            top_scores.append(top.score)
            top_retrievability.append(
                self.curve.retrievability(top.item, now)
            )
            if any(
                "overlap" in reason or "semantic" in reason
                for reason in top.reasons
            ):
                hit_count += 1
            else:
                weak_count += 1
        evaluated = len(queries)
        hit_rate = (
            round(hit_count / evaluated, 3) if evaluated else 0.0
        )
        weak_rate = (
            round(weak_count / evaluated, 3) if evaluated else 0.0
        )
        verdict = (
            "good" if hit_rate >= 0.8 else (
                "fair" if hit_rate >= 0.5 else "poor"
            )
        )
        return {
            "queries_evaluated": evaluated,
            "hit_count": hit_count,
            "weak_count": weak_count,
            "avg_top_score": round(
                sum(top_scores) / max(1, len(top_scores)), 3
            ),
            "avg_top_retrievability": round(
                sum(top_retrievability) / max(1, len(top_retrievability)),
                3,
            ),
            "hit_rate": hit_rate,
            "weak_rate": weak_rate,
            "verdict": verdict,
        }
    def recall_trace(
        self,
        query: str,
        top_k: int = 5,
    ) -> dict:
        """Explain why a query recalls what it recalls.

        Metacognitive explanation (Koriat & Goldsmith, 1996): show how
        many candidates were scanned, the top results with scores and
        per-result reasons, so agents can audit their own retrieval.
        """
        candidates = self.store.all_active()
        results = self.recall(query, top_k=max(1, int(top_k)))
        traced = [
            {
                "id": result.item.id,
                "preview": result.item.content[:40],
                "score": round(result.score, 3),
                "confident": result.confident,
                "reasons": result.reasons[:6],
            }
            for result in results
        ]
        top = traced[0] if traced else None
        return {
            "query": query,
            "candidates_scanned": len(candidates),
            "results": traced,
            "top_reason_summary": (
                "; ".join(top["reasons"][:3]) if top else None
            ),
        }
    def community_report(
        self,
        limit: int = 10,
    ) -> dict:
        """Detect memory communities in the association network.

        Semantic networks have modular structure (community detection):
        strongly linked memories form clusters. This uses connected
        components so agents can see which memories form a theme-cluster
        and which are isolated.
        """

        items = self.store.all_active()
        parent = {item.id: item.id for item in items}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: str, b: str) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra

        for src, dst, _weight in self.backend.all_links():
            if src in parent and dst in parent:
                union(src, dst)
        groups: dict[str, list] = defaultdict(list)
        for item in items:
            groups[find(item.id)].append(item)
        communities = []
        for root, members in groups.items():
            cue_counts: Counter = Counter()
            for member in members:
                for cue in member.cues:
                    cue_counts[cue] += 1
            communities.append(
                {
                    "id": root,
                    "size": len(members),
                    "members": [
                        {
                            "id": member.id,
                            "preview": member.content[:24],
                        }
                        for member in members[:4]
                    ],
                    "top_cues": [
                        cue for cue, _count in cue_counts.most_common(3)
                    ],
                }
            )
        communities.sort(key=lambda community: -community["size"])
        return {
            "total_communities": len(communities),
            "largest_size": (
                communities[0]["size"] if communities else 0
            ),
            "communities": communities[: max(1, int(limit))],
        }
    def schema_report(self, limit: int = 20) -> dict:
        """Group memories into topic schemas by their primary cue.

        Schema theory (Bartlett, 1932; event schemas, Gilboa & Marlatte,
        2017): the mind organizes related experiences under shared
        scripts/topics. This report clusters active memories by their
        primary cue and shows each cluster's size, average importance,
        kind mix and content samples, so agents can see what topics their
        memory store actually covers.
        """
        groups: dict[str, dict] = {}
        for item in self.store.all_active():
            topic = item.cues[0] if item.cues else "（无标签）"
            group = groups.setdefault(
                topic,
                {
                    "topic": topic,
                    "memory_count": 0,
                    "avg_importance": 0.0,
                    "kinds": {"semantic": 0, "episodic": 0},
                    "samples": [],
                },
            )
            group["memory_count"] += 1
            group["avg_importance"] += item.importance
            group["kinds"][item.kind.value] += 1
            if len(group["samples"]) < 3:
                group["samples"].append(item.content[:24])
        out = []
        for group in groups.values():
            group["avg_importance"] = round(
                group["avg_importance"] / group["memory_count"], 3
            )
            out.append(group)
        out.sort(key=lambda g: (-g["memory_count"], g["topic"]))
        return {
            "total_memories": len(self.store.all_active()),
            "group_count": len(out),
            "top_groups": out[: max(1, int(limit))],
        }
    def recall_reasoning(
        self,
        query: str,
        *,
        top_k: int | None = None,
        now: datetime | None = None,
    ) -> list[RecallResult]:
        """System-2 recall: assemble a reasoning premise pack.

        Fast keyword retrieval (System 1) plus a bounded boost for all
        same-dimension premises (math / compare / transitive questions), so
        the full premise set reaches the LLM context (Kahneman 2011;
        Miller & Cohen 2001).
        """

        return self.recall(
            query,
            top_k=top_k or suggested_pack_size(query),
            now=now,
            reasoning_pack=True,
        )
    def recall_steps(
        self,
        query: str,
        *,
        top_k: int = 10,
        now: datetime | None = None,
        zh_synonyms: bool = True,
        plan_reuse: bool = True,
    ) -> list[RecallResult]:
        """Chain-of-thought step retrieval for process questions.

        "怎么 / 如何 / 为什么" questions need the ordered intermediate
        steps, not a keyword soup: mental time travel (Tulving, 1985) and
        event schemas (Gilboa & Marlatte, 2017) organize episodes into a
        chronological script, and chain-of-thought reasoning (Wei et al.,
        2022) consumes those steps in order. Episodic results are sorted by
        event date; non-process questions behave exactly like
        ``recall_reasoning``.
        """


        results = self.recall(
            query,
            top_k=max(top_k * 2, 16),
            now=now,
            reasoning_pack=True,
            zh_synonyms=zh_synonyms,
        )
        if not any(marker in query for marker in (
            "怎么", "如何", "为什么", "过程", "步骤", "准备", "计划", "安排",
            "第一步", "该做什么", "怎么做", "流程", "方法", "办法", "方式",
            "想", "要", "打算", "希望",
            "how", "why", "step",
        )):
            return results[:top_k]

        def _event_date(result) -> str:
            content = result.item.content
            match = re.search(r"\d{4}-\d{2}-\d{2}", content)
            if match:
                return match.group(0)
            match = re.search(
                r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日",
                content,
            )
            if match:
                return (
                    f"{int(match.group(1)):04d}-"
                    f"{int(match.group(2)):02d}-"
                    f"{int(match.group(3)):02d}"
                )
            return "9999-12-31"

        episodic = [
            r for r in results
            if r.item.kind is MemoryKind.EPISODIC
            and "执行成功" not in r.item.content
            and "执行失败" not in r.item.content
        ]
        others = [
            r for r in results if r.item.kind is not MemoryKind.EPISODIC
        ]
        ref_persons: list[str] = []
        if plan_reuse:

            found = re.findall(
                r"(?:参考|参照|学|模仿|按照|像)([\u4e00-\u9fff]{2})"
                r"|和([\u4e00-\u9fff]{2})",
                query,
            )
            ref_persons = [
                (a or b) for a, b in found if (a or b)
            ]
            if ref_persons:

                query_terms = expand_synonyms(set(tokenize(query)))
                _TOPIC_STOP = {
                    "怎么", "如何", "准备", "计划", "参考", "参照", "模仿",
                    "按照", "更好", "希望", "想要", "想做", "打算", "安排",
                }
                topic_terms = [
                    t for t in query_terms
                    if t not in ref_persons
                    and t not in _TOPIC_STOP
                    and len(t) > 1
                ][:4]
                topic = " ".join(topic_terms)
                existing_ids = {r.item.id for r in episodic}
                for ref_person in ref_persons:
                    extra = self.recall(
                        f"{ref_person} {topic}".strip(),
                        top_k=8,
                        now=now,
                        kind=MemoryKind.EPISODIC,
                        reasoning_pack=True,
                        zh_synonyms=zh_synonyms,
                    )
                    for r in extra:
                        if (
                            r.item.kind is not MemoryKind.EPISODIC
                            or r.item.id in existing_ids
                            or "执行成功" in r.item.content
                            or "执行失败" in r.item.content
                        ):
                            continue
                        if (
                            ref_person not in r.item.cues
                            and ref_person not in r.item.content
                        ):
                            continue
                        episodic.append(r)
                        existing_ids.add(r.item.id)
                        if not any(
                            "\u7c7b\u6bd4\u8ba1\u5212" in reason
                            for reason in r.reasons
                        ):
                            r.reasons.append(
                                "\u7c7b\u6bd4\u8ba1\u5212(\u53c2\u8003"
                                f"{ref_person})"
                            )
            ref_persons_all = ref_persons
            if ref_persons_all:
                ref_person = ref_persons_all[0]
                for r in episodic:
                    if (
                        ref_person in r.item.cues
                        or ref_person in r.item.content
                    ):
                        r.score = round(r.score + 0.08, 4)
                        if not any(
                            "类比计划" in reason for reason in r.reasons
                        ):
                            r.reasons.append(
                                "\u7c7b\u6bd4\u8ba1\u5212(\u53c2\u8003"
                                f"{ref_person})"
                            )
        def _plan_key(result) -> tuple:
            person = (
                result.item.cues[0][:2]
                if result.item.cues
                else result.item.content[:2]
            )
            ref_priority = 0 if person in ref_persons else 1
            return (ref_priority, _event_date(result))

        episodic.sort(key=_plan_key)
        ordered = episodic + others
        for result in episodic:
            if not any("步骤" in reason for reason in result.reasons):
                result.reasons.append(
                    "\u601d\u7ef4\u94fe\u6b65\u9aa4(\u6309\u65f6\u95f4\u6392\u5e8f)"
                )
        return ordered[:top_k]
    def review_consistency(
        self,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Monitor adherence to the spaced-review schedule (SRL).

        Spacing only works when reviews actually happen at the scheduled
        time (Cepeda et al., 2006), and monitoring one's own study
        behavior is a core self-regulated-learning skill (Zimmerman).
        For every memory with review history this computes the next
        scheduled review from its last review, flags past-due items,
        and reports an adherence ratio with plain advice.
        """
        now = now or utcnow()
        reviewed = []
        never_reviewed = 0
        for item in self.store.all_active():
            if item.last_review_at is None:
                never_reviewed += 1
                continue
            due_at = self.scheduler.next_review_at(
                item, now=item.last_review_at
            )
            overdue = now > due_at
            lateness_days = max(0, (now - due_at).days)
            reviewed.append(
                {
                    "memory_id": item.id,
                    "preview": item.content[:32],
                    "review_streak": item.review_streak,
                    "last_review_at": item.last_review_at.isoformat(),
                    "scheduled_at": due_at.isoformat(),
                    "overdue": overdue,
                    "lateness_days": lateness_days,
                }
            )
        reviewed.sort(key=lambda row: -row["lateness_days"])
        on_time = sum(1 for row in reviewed if not row["overdue"])
        total_reviewed = len(reviewed)
        adherence_ratio = round(
            on_time / max(1, total_reviewed), 3
        )
        avg_lateness = round(
            sum(row["lateness_days"] for row in reviewed)
            / max(1, total_reviewed),
            2,
        )
        if adherence_ratio >= 0.8:
            verdict = "high"
        elif adherence_ratio >= 0.5:
            verdict = "medium"
        else:
            verdict = "low"
        if total_reviewed == 0:
            advice = (
                "还没有复习记录：间隔复习只有真复习才有用，"
                "先从到期记忆开始每天复习。"
            )
        elif verdict == "high":
            advice = (
                f"坚持度 {adherence_ratio:.0%}：复习很准时，"
                "保持这个节奏，重点看最晚到期的几条。"
            )
        elif verdict == "medium":
            advice = (
                f"坚持度 {adherence_ratio:.0%}：一半左右复习在到期后补做，"
                "把复习固定到固定时段，先清积压再上新。"
            )
        else:
            advice = (
                f"坚持度 {adherence_ratio:.0%}：积压较多，"
                "建议先只复习最危险（最重要+最晚到期）的几条，"
                "恢复节奏后再扩量。"
            )
        return {
            "total_memories": len(reviewed) + never_reviewed,
            "reviewed_count": total_reviewed,
            "on_time_count": on_time,
            "overdue_count": total_reviewed - on_time,
            "never_reviewed_count": never_reviewed,
            "adherence_ratio": adherence_ratio,
            "avg_lateness_days": avg_lateness,
            "verdict": verdict,
            "top_overdue": reviewed[:3],
            "advice": advice,
        }
    def similarity_report(
        self,
        threshold: float = 0.6,
        limit: int = 20,
    ) -> list[dict]:
        """Find confusable memory pairs by content-token overlap.

        Helps agents spot near-duplicates that dedupe may have missed or
        pairs that need better separation (pattern separation; Yassa &
        Stark, 2011).
        """

        items = self.store.all_active()
        pairs = []
        for i in range(len(items)):
            a = items[i]
            a_terms = set(tokenize(a.content))
            for j in range(i + 1, len(items)):
                b = items[j]
                b_terms = set(tokenize(b.content))
                common = len(a_terms & b_terms)
                denominator = max(1, min(len(a_terms), len(b_terms)))
                overlap = common / denominator
                if overlap >= threshold:
                    pairs.append(
                        {
                            "a_id": a.id,
                            "b_id": b.id,
                            "overlap": round(overlap, 3),
                            "a_preview": a.content[:40],
                            "b_preview": b.content[:40],
                        }
                    )
        pairs.sort(key=lambda p: p["overlap"], reverse=True)
        return pairs[: max(1, int(limit))]
    def association_report(self, limit: int = 10) -> dict:
        """Summarize the memory association network.

        Reports how well memories are interlinked (spreading activation;
        Collins & Loftus, 1975): total links, connected vs isolated
        memories, average degree, and the most-connected memories.
        """
        items = {item.id: item for item in self.store.all_active()}
        links = self.backend.all_links()
        degree: dict[str, int] = {mid: 0 for mid in items}
        unique_pairs: set[frozenset[str]] = set()
        directed = 0
        for src, dst, _weight in links:
            if src in items and dst in items:
                directed += 1
                degree[src] += 1
                degree[dst] += 1
                unique_pairs.add(frozenset((src, dst)))
        connected = sum(1 for d in degree.values() if d > 0)
        top = sorted(
            degree.items(), key=lambda kv: (-kv[1], kv[0])
        )[: max(1, int(limit))]
        top_connected = [
            {
                "id": mid,
                "preview": items[mid].content[:40],
                "link_count": degree[mid],
                "kind": items[mid].kind.value,
            }
            for mid, _count in top
            if degree[mid] > 0
        ]
        return {
            "memory_count": len(items),
            "directed_links": directed,
            "unique_pairs": len(unique_pairs),
            "connected_count": connected,
            "isolated_count": len(items) - connected,
            "avg_links": round(
                sum(degree.values()) / max(1, len(items)), 3
            ),
            "top_connected": top_connected,
        }
