"""Analysis mixin: reports, metacognition and learning advice."""

from __future__ import annotations

import random
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from itertools import combinations

from .reasoning import suggested_pack_size
from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    RecallResult,
    SourceRecord,
    SourceType,
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
    def sleep_advice(self, now: datetime | None = None) -> dict:
        """Advise what to review before sleep for better consolidation.

        Sleep consolidates memories, and pre-sleep rehearsal of important
        material strengthens it (Rasch & Born, 2013). This tool collects
        weak-but-important memories to review before sleep, plus conflicts,
        overdue intentions and tomorrow's unreviewed topics.
        """
        items = self.store.all_active()
        weak_important = [
            item for item in items
            if item.importance >= 0.6
            and self.curve.retrievability(item, now) < 0.5
        ]
        weak_important.sort(key=lambda item: -item.importance)
        pre_sleep_review = [
            {
                "id": item.id,
                "preview": item.content[:40],
                "importance": round(item.importance, 3),
                "retrievability": round(
                    self.curve.retrievability(item, now), 3
                ),
            }
            for item in weak_important[:5]
        ]
        conflicts = len(self.consolidator.detect_conflicts())
        queue = self.action_queue(now=now)
        coverage = self.coverage_report(now=now)
        tomorrow_priorities = [
            {
                "topic": topic["topic"],
                "memory_count": topic["memory_count"],
                "coverage": topic["coverage"],
            }
            for topic in coverage["topics"]
            if topic["status"] == "unreviewed"
        ][:3]
        advice = (
            "睡前先过一遍“重要但快忘”的记忆，"
            "冲突留到明天集中处理，过期待办尽快收尾"
        )
        return {
            "pre_sleep_review": pre_sleep_review,
            "conflicts_to_resolve": conflicts,
            "overdue_intents": queue["overdue"],
            "tomorrow_priorities": tomorrow_priorities,
            "advice": advice,
        }
    def emotion_advice(
        self,
        memory_ids: list[str] | None = None,
    ) -> dict:
        """Profile emotional tone of memories and advise regulation.

        Emotion regulation (Gross, 2002) starts with awareness of the
        emotional load: this tool counts positive/negative/neutral/
        arousing traces, reports the negative ratio and suggests
        reappraisal or spacing when negativity is high.
        """

        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        else:
            items = self.store.all_active()
        counts = Counter(
            item.affect or "neutral" for item in items
        )
        total = len(items)
        negative = counts["negative"]
        negative_ratio = round(negative / max(1, total), 3)
        flagged_topics = []
        topic_negative: dict[str, int] = {}
        for item in items:
            if item.affect == "negative" and item.cues:
                topic = item.cues[0]
                topic_negative[topic] = topic_negative.get(topic, 0) + 1
        for topic, count in sorted(
            topic_negative.items(), key=lambda kv: -kv[1]
        )[:3]:
            flagged_topics.append({"topic": topic, "negative_count": count})
        if negative_ratio >= 0.4:
            advice = (
                "消极记忆占比偏高：先重评一次（换个角度看待），"
                "重要的单独处理，避免整体情绪被带偏"
            )
        elif negative_ratio >= 0.2:
            advice = (
                "消极记忆有一定占比：建议逐条重评，"
                "把“当时很糟”改写为“当时学到什么”"
            )
        else:
            advice = "情绪分布较均衡，保持现状即可"
        return {
            "total_memories": total,
            "mood_profile": {
                "positive": counts["positive"],
                "negative": counts["negative"],
                "neutral": counts["neutral"],
                "arousing": counts["arousing"],
                "mixed": counts["mixed"],
            },
            "negative_ratio": negative_ratio,
            "flagged_topics": flagged_topics,
            "advice": advice,
        }
    def difficulty_estimator(
        self,
        limit: int = 10,
        now: datetime | None = None,
    ) -> dict:
        """Estimate current learning difficulty of each memory.

        Desirable difficulties (Bjork, 1994): learning benefits most when
        retrieval is effortful but still possible. This tool buckets every
        active memory by current retrievability into too-easy / sweet-spot /
        hard / very-hard, highlights the sweet-spot workload and gives
        concrete next actions per bucket.
        """
        items = self.store.all_active()
        buckets = {"too_easy": 0, "sweet_spot": 0, "hard": 0, "very_hard": 0}
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            if r >= 0.75:
                level = "too_easy"
            elif r >= 0.35:
                level = "sweet_spot"
            elif r >= 0.12:
                level = "hard"
            else:
                level = "very_hard"
            buckets[level] += 1
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "level": level,
                    "retrievability": round(r, 3),
                    "importance": round(item.importance, 3),
                    "reviews": item.review_streak,
                }
            )
        rows.sort(key=lambda row: (-row["importance"], row["retrievability"]))
        total = len(items)
        sweet_ratio = round(buckets["sweet_spot"] / max(1, total), 3)
        topic_rows: list[dict] = []
        topic_buckets: dict[str, dict] = {}
        for row in rows:
            entry = topic_buckets.setdefault(
                row["topic"],
                {
                    "topic": row["topic"],
                    "count": 0,
                    "sweet_spot": 0,
                    "hard": 0,
                    "very_hard": 0,
                },
            )
            entry["count"] += 1
            if row["level"] == "sweet_spot":
                entry["sweet_spot"] += 1
            elif row["level"] == "hard":
                entry["hard"] += 1
            elif row["level"] == "very_hard":
                entry["very_hard"] += 1
        for entry in topic_buckets.values():
            if entry["count"] >= 2:
                topic_rows.append(entry)
        topic_rows.sort(
            key=lambda entry: (-entry["very_hard"], -entry["hard"], -entry["count"])
        )
        if buckets["very_hard"] and sweet_ratio < 0.3:
            advice = (
                "太难的太多：先给小步重编码（加线索、拆成更小的点），"
                "把 very_hard 拉回 hard 再进 sweet_spot，不要直接硬背。"
            )
        elif buckets["too_easy"] and sweet_ratio < 0.3:
            advice = (
                "太容易的太多：容易的推迟复习（间隔），等它掉进"
                " sweet_spot 再练，避免假熟练。"
            )
        elif sweet_ratio >= 0.3:
            advice = (
                "难度分布良好：重点保持 sweet_spot 节奏，"
                "太难的拆解、太容易的延后。"
            )
        else:
            advice = "按 importance 优先：sweet_spot 先练，hard 拆解，very_hard 重编码。"
        return {
            "total_memories": total,
            "buckets": buckets,
            "sweet_spot_ratio": sweet_ratio,
            "rows": rows[: max(1, int(limit))],
            "topic_summary": topic_rows[:5],
            "advice": advice,
        }
    def memory_integration(
        self,
        limit: int = 10,
        now: datetime | None = None,
    ) -> dict:
        """Suggest how related memories can be integrated or composed.

        Compositional inference in the hippocampal-prefrontal circuit
        (Schwartenbeck et al., 2023; Spens & Burgess, 2024): related
        traces replayed together form higher-level schemas; nearby
        episodes form event chains; unresolved contradictions block
        clean integration.
        """

        items = self.store.all_active()
        topic_groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        member_links: set[frozenset[str]] = set()
        for src, dst, _weight in self.backend.all_links():
            member_links.add(frozenset({src, dst}))

        schema_candidates: list[dict] = []
        event_chains: list[dict] = []
        for topic, members in topic_groups.items():
            member_ids = {member.id for member in members}
            linked_pairs = sum(
                1
                for pair in member_links
                if pair <= member_ids and len(pair) == 2
            )
            if len(members) >= 2:
                avg_importance = round(
                    sum(member.importance for member in members)
                    / len(members),
                    3,
                )
                schema_candidates.append(
                    {
                        "topic": topic,
                        "count": len(members),
                        "avg_importance": avg_importance,
                        "linked_pairs": linked_pairs,
                        "suggestion": (
                            "把同主题记忆重放并整合成一条总结记忆"
                            "（组合推理），减少碎片化"
                        ),
                    }
                )
            episodes = [
                member
                for member in members
                if member.kind == MemoryKind.EPISODIC
                and member.source.occurred_at is not None
            ]
            episodes.sort(key=lambda member: member.source.occurred_at)  # type: ignore[arg-type]
            chain = episodes
            if len(chain) >= 2:
                span_days = round(
                    (
                        chain[-1].source.occurred_at
                        - chain[0].source.occurred_at
                    ).total_seconds()
                    / 86400.0,
                    1,
                )
                if span_days <= 14:
                    event_chains.append(
                        {
                            "topic": topic,
                            "events": len(chain),
                            "span_days": span_days,
                            "suggestion": (
                                "把这段时间内的事件串成一条事件链，"
                                "回忆时按顺序重放"
                            ),
                        }
                    )
        schema_candidates.sort(
            key=lambda candidate: (
                -candidate["count"],
                -candidate["avg_importance"],
            )
        )
        event_chains.sort(key=lambda chain: -chain["events"])
        conflicts = self.consolidator.detect_conflicts()
        if conflicts:
            advice = (
                "先解决冲突再整合：同主题记忆互相矛盾时，"
                "先裁定哪条更可信，再合成总结。"
            )
        elif schema_candidates:
            advice = (
                "整合时机已到：同主题记忆可以重放整合成高层图式，"
                "近段事件可以串成事件链。"
            )
        else:
            advice = "当前记忆较分散，暂无整合候选；持续记录后会自动出现。"
        return {
            "total_memories": len(items),
            "schema_candidates": schema_candidates[: max(1, int(limit))],
            "event_chains": event_chains[: max(1, int(limit))],
            "conflicts": len(conflicts),
            "advice": advice,
        }
    def reasoning_trace(
        self,
        problem: str,
        *,
        topic: str | None = None,
        top_k: int = 4,
        store_conclusion: bool = True,
        now: datetime | None = None,
    ) -> dict:
        """Build a replay-friendly reasoning trace from stored memories.

        Mathematical reasoning relies on working memory + prefrontal
        control over quantity representations (Menon, 2016; Dehaene),
        and complex problem solving cycles through goal states that are
        replayed (Watanabe et al., 2023; Jensen et al., 2024). This tool
        recalls premise memories relevant to the problem, extracts the
        quantities, builds a step trace with per-step evidence, and can
        store the derived conclusion as an inference memory so the next
        reasoning round starts from a richer base.
        """

        topic = topic or (self.store.all_active()[0].cues[0] if self.store.all_active() else problem[:12])
        results = self.recall(problem, top_k=max(1, int(top_k)), now=now)
        evidence = [
            {
                "id": result.item.id,
                "preview": result.item.content[:48],
                "confidence": round(result.item.confidence, 3),
                "score": round(result.score, 3),
            }
            for result in results
            if result.score >= 0.05
        ]
        numbers: list[dict] = []
        seen: set[tuple[str, str]] = set()
        for text in [problem] + [item["preview"] for item in evidence]:
            for raw in re.findall(r"-?\d+(?:\.\d+)?", text):
                key = (raw, text[:20])
                if key in seen:
                    continue
                seen.add(key)
                numbers.append(
                    {
                        "value": float(raw),
                        "raw": raw,
                        "where": "problem" if text == problem else "memory",
                    }
                )
        steps = [
            {
                "order": 1,
                "step": "读题：列出已知条件",
                "evidence_ids": [item["id"] for item in evidence],
                "verdict": "ok" if evidence else "weak",
            },
            {
                "order": 2,
                "step": "从记忆中核对已知量",
                "evidence_ids": [item["id"] for item in evidence[:2]],
                "verdict": "ok" if len(numbers) >= 2 else "weak",
            },
            {
                "order": 3,
                "step": "按数量关系计算",
                "evidence_ids": [item["id"] for item in evidence[:1]],
                "verdict": "ok" if numbers else "weak",
            },
            {
                "order": 4,
                "step": "得出结论并准备固化",
                "evidence_ids": [],
                "verdict": "ok",
            },
        ]
        stored_id = None
        if store_conclusion and evidence:
            conclusion = (
                f"推理结论：{problem}（依据 {len(evidence)} 条记忆，"
                f"提取 {len(numbers)} 个数量）"
            )
            item = self.remember(
                conclusion,
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.INFERENCE),
                cues=[topic],
                importance=0.6,
                confidence=0.7,
                evidence_count=len(evidence),
                auto_cues=False,
            )
            stored_id = item.id
        return {
            "problem": problem,
            "topic": topic,
            "evidence_used": evidence[: max(1, int(top_k))],
            "numbers": numbers,
            "steps": steps,
            "verdict": "consistent" if evidence else "review_needed",
            "stored_memory_id": stored_id,
            "advice": (
                "推理链已按记忆证据逐步展开；结论已存入记忆库，"
                "下次同类问题可直接引用。"
                if stored_id
                else "证据不足：先补充相关记忆，再重新推理。"
            ),
        }
    def sleep_inference(
        self,
        *,
        limit: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Find memory pairs that sleep can weave into new inferences.

        NREM/REM sleep coordinates the weaving of inferential knowledge:
        the brain replays learned pairs offline and the prefrontal cortex
        codes the inferred outcome (Abdou, Nomoto et al., Nature
        Communications, 2024). This tool finds same-topic memory pairs
        that are consolidated enough to support a new inference, ranks
        them by readiness, and tells the agent what to "let sleep
        integrate" next.
        """

        items = self.store.all_active()
        topic_groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        candidates: list[dict] = []
        for topic, members in topic_groups.items():
            for i in range(len(members)):
                for j in range(i + 1, len(members)):
                    a, b = members[i], members[j]
                    if a.content_hash == b.content_hash:
                        continue
                    shared_cues = len(set(a.cues) & set(b.cues))
                    ra = self.curve.retrievability(a, now)
                    rb = self.curve.retrievability(b, now)
                    need_consolidation = int(
                        min(ra, rb) < 0.6
                        and min(a.importance, b.importance) >= 0.4
                    )
                    readiness = round(
                        min(1.0, 0.5 * min(1.0, shared_cues)
                            + 0.5 * need_consolidation),
                        3,
                    )
                    candidates.append(
                        {
                            "topic": topic,
                            "a_preview": a.content[:36],
                            "b_preview": b.content[:36],
                            "shared_cues": shared_cues,
                            "retrievability_a": round(ra, 3),
                            "retrievability_b": round(rb, 3),
                            "readiness": readiness,
                            "reason": (
                                "同一主题、遗忘到需要巩固的程度，"
                                "睡眠重放后可组合出新推断"
                            ),
                        }
                    )
        candidates.sort(key=lambda candidate: -candidate["readiness"])
        ready = [candidate for candidate in candidates if candidate["readiness"] >= 0.5]
        return {
            "total_pairs": len(candidates),
            "ready_pairs": len(ready),
            "candidates": candidates[: max(1, int(limit))],
            "advice": (
                "睡眠整合窗口：已找到可组合的推断对，"
                "睡前复习一遍、睡后再查一次，把新推断补进记忆库。"
                if ready
                else "暂无可组合推断对：继续积累同主题记忆，睡眠后再看。"
            ),
        }
    def schema_fit(
        self,
        *,
        limit: int = 20,
    ) -> dict:
        """Measure how new memories fit existing schemas.

        Schemas speed up consolidation: memories congruent with an
        existing schema integrate rapidly in the neocortex (Tse et al.,
        Science, 2007), and reconstruction follows assimilation or
        accommodation (Bartlett, 1932). This tool scores each memory's
        fit to the best-matching schema (topic group) and labels it
        assimilate / borderline / accommodate.
        """


        items = self.store.all_active()
        groups: dict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            groups[topic].append(item)
        schemas = {
            topic: members
            for topic, members in groups.items()
            if len(members) >= 2
        }
        rows: list[dict] = []
        for item in items:
            best_topic = None
            best_fit = 0.0
            item_cues = set(item.cues)
            item_terms = set(tokenize(item.content))
            for topic, members in schemas.items():
                if any(member.id == item.id for member in members):
                    members = [member for member in members if member.id != item.id]
                    if not members:
                        continue
                cue_union: set[str] = set()
                term_union: set[str] = set()
                for member in members:
                    cue_union.update(member.cues)
                    term_union.update(tokenize(member.content))
                cue_overlap = (
                    len(item_cues & cue_union) / max(1, len(item_cues | cue_union))
                    if (item_cues or cue_union)
                    else 0.0
                )
                term_overlap = (
                    len(item_terms & term_union) / max(1, len(item_terms | term_union))
                    if (item_terms or term_union)
                    else 0.0
                )
                fit = min(1.0, 0.6 * cue_overlap + 0.4 * term_overlap)
                if fit > best_fit:
                    best_fit = fit
                    best_topic = topic
            verdict = (
                "assimilate"
                if best_fit >= 0.5
                else "borderline"
                if best_fit >= 0.3
                else "accommodate"
            )
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "topic": item.cues[0] if item.cues else item.content[:10],
                    "best_schema": best_topic,
                    "fit": round(best_fit, 3),
                    "verdict": verdict,
                }
            )
        counts = defaultdict(int)
        for row in rows:
            counts[row["verdict"]] += 1
        schema_summary = []
        for topic, members in schemas.items():
            schema_rows = [row for row in rows if row["topic"] == topic]
            avg_fit = round(
                sum(row["fit"] for row in schema_rows) / max(1, len(schema_rows)),
                3,
            )
            schema_summary.append(
                {
                    "topic": topic,
                    "member_count": len(members),
                    "avg_fit": avg_fit,
                    "assimilate": sum(
                        1 for row in schema_rows if row["verdict"] == "assimilate"
                    ),
                    "accommodate": sum(
                        1 for row in schema_rows if row["verdict"] == "accommodate"
                    ),
                }
            )
        schema_summary.sort(key=lambda s: -s["member_count"])
        if counts["accommodate"] > counts["assimilate"]:
            advice = "新知识不成体系：多数记忆找不到合适图式，建议先建新图式再积累。"
        elif counts["assimilate"] >= max(1, counts["accommodate"]):
            advice = "记忆正顺利并入现有图式：与图式一致的记忆巩固更快（Tse 2007）。"
        else:
            advice = "有图式可并入，也有新图式在形成，按主题分别维护即可。"
        return {
            "total_memories": len(items),
            "schema_count": len(schemas),
            "rows": rows[: max(1, int(limit))],
            "verdict_counts": dict(counts),
            "schema_summary": schema_summary,
            "advice": advice,
        }
    def test_generator(
        self,
        *,
        topic: str | None = None,
        memory_ids: list[str] | None = None,
        count: int = 4,
    ) -> dict:
        """Generate retrieval-practice questions without giving answers.

        Testing effect (Roediger & Karpicke, 2006): taking a test on
        material beats re-reading it. This tool turns memories into
        cue-prompt and cloze questions (answers hidden) so the agent can
        self-quiz and then score with practice_answer.
        """
        if memory_ids:
            items = []
            for memory_id in memory_ids:
                item = self.backend.get(memory_id)
                if item is not None:
                    items.append(item)
        elif topic:
            items = [
                item
                for item in self.store.all_active()
                if topic in item.cues or topic in item.content
            ]
        else:
            items = self.store.all_active()
        items = items[: max(1, int(count))]
        questions: list[dict] = []
        for index, item in enumerate(items):
            content = item.content
            cue = item.cues[0] if item.cues else content[:10]
            if index % 2 == 0:
                question = (
                    f"【测试】提示词“{cue}”：请回忆这条记忆讲了什么。"
                )
                qtype = "cue_prompt"
            else:
                blank = "____"
                if len(content) > 8:
                    blank_len = min(4, max(2, len(content) // 3))
                    blank = "____" * max(1, blank_len // 4)
                    question = content[:-blank_len] + blank
                else:
                    question = f"【测试】请补全：{blank}（提示：{cue}）"
                qtype = "cloze"
            questions.append(
                {
                    "memory_id": item.id,
                    "question": question,
                    "qtype": qtype,
                    "hint_cues": item.cues[:3],
                    "answer_hidden": True,
                }
            )
        return {
            "topic": topic,
            "question_count": len(questions),
            "questions": questions,
            "advice": (
                "先自测再对答案：测试比重读记得牢（Roediger & Karpicke 2006）；"
                "答完用 practice_answer 打分并强化。"
            ),
        }
    def rumination_check(
        self,
        *,
        access_threshold: int = 5,
    ) -> dict:
        """Detect repeated retrieval of negative memories (rumination).

        Repetitive negative thinking is a transdiagnostic risk factor
        (Watkins, 2008; Ehring & Watkins, 2008), while reactivation makes
        a memory labile so it can be updated rather than merely replayed
        (Nader et al., 2000). This tool flags negative/arousing memories
        that are accessed far too often and suggests reappraisal +
        update instead of another replay.
        """

        threshold = max(1, int(access_threshold))
        items = self.store.all_active()
        risky: list[dict] = []
        negative_count = 0
        for item in items:
            if item.affect not in ("negative", "arousing"):
                continue
            negative_count += 1
            if item.access_count >= threshold:
                risky.append(
                    {
                        "id": item.id,
                        "preview": item.content[:36],
                        "affect": item.affect,
                        "access_count": item.access_count,
                        "topic": item.cues[0] if item.cues else item.content[:10],
                    }
                )
        topic_counts: defaultdict[str, int] = defaultdict(int)
        for item in risky:
            topic_counts[item["topic"]] += 1
        rumination_topics = [
            {"topic": topic, "risky_count": count}
            for topic, count in sorted(
                topic_counts.items(), key=lambda kv: -kv[1]
            )
        ]
        if len(risky) >= 3 or any(
            topic["risky_count"] >= 2 for topic in rumination_topics
        ):
            risk_level = "high"
        elif risky:
            risk_level = "medium"
        else:
            risk_level = "low"
        if risk_level == "high":
            advice = (
                "反刍风险高：同一件负性事件被反复调出。别再重复回放，"
                "先重评（换个角度），再借“提取后记忆可更新”的窗口"
                "改写结论（Nader 2000）。"
            )
        elif risk_level == "medium":
            advice = (
                "有反刍苗头：这条负性记忆被访问偏多。"
                "建议改为间隔复习 + 重评，而不是每次想起来就重放。"
            )
        else:
            advice = "情绪记忆访问正常：保持间隔复习即可。"
        return {
            "total_memories": len(items),
            "negative_count": negative_count,
            "risky_memories": risky,
            "rumination_topics": rumination_topics,
            "risk_level": risk_level,
            "advice": advice,
        }
    def consolidation_forecast(
        self,
        *,
        limit: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Predict which memories will benefit most from sleep.

        Sleep consolidates memory, and pre-sleep rehearsal of important
        material strengthens it (Rasch & Born, 2013). Emotional salience
        also boosts overnight consolidation (Cahill & McGaugh, 1998).
        This tool scores every memory's overnight-gain potential and
        returns tonight's review candidates with predicted gain.
        """
        items = self.store.all_active()
        rows: list[dict] = []
        for item in items:
            r = self.curve.retrievability(item, now)
            emotional = int(
                item.affect in ("positive", "negative", "arousing", "mixed")
            )
            weak_boost = 0.5 if r < 0.6 else 0.0
            score = round(
                min(
                    1.0,
                    0.4 * item.importance
                    + 0.3 * emotional
                    + 0.3 * weak_boost,
                ),
                3,
            )
            gain = round(max(0.0, 1.0 - r) * item.importance, 3)
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:36],
                    "importance": round(item.importance, 3),
                    "affect": item.affect or "neutral",
                    "retrievability": round(r, 3),
                    "consolidation_score": score,
                    "predicted_gain": gain,
                    "reason": (
                        "重要 + 情绪显著 + 需要巩固，睡眠收益最大"
                        if score >= 0.8
                        else "重要或情绪记忆，睡前过一遍可强化"
                        if score >= 0.5
                        else "巩固收益一般，按常规间隔复习即可"
                    ),
                }
            )
        rows.sort(
            key=lambda row: (
                -row["consolidation_score"],
                -row["predicted_gain"],
            )
        )
        top = rows[: max(1, int(limit))]
        return {
            "total_memories": len(items),
            "tonight_candidates": top,
            "predicted_gain_total": round(
                sum(row["predicted_gain"] for row in top), 3
            ),
            "advice": (
                "睡前把今晚候选快速过一遍，睡后巩固效果最好"
                "（Rasch & Born 2013）。"
                if top
                else "暂无高收益候选，保持常规复习即可。"
            ),
        }
    def forgetting_balance(
        self,
        *,
        imbalance_ratio: float = 3.0,
        limit: int = 10,
    ) -> dict:
        """Detect within-topic access imbalance (retrieval-induced forgetting).

        Retrieving one memory strengthens it and suppresses its
        competitors in the same category (Anderson, Bjork & Bjork, 1994).
        If one memory in a topic is retrieved far more often than its
        siblings, the siblings may be losing retrievability silently.
        """

        ratio = max(1.0, float(imbalance_ratio))
        items = self.store.all_active()
        topic_groups: defaultdict[str, list] = defaultdict(list)
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            topic_groups[topic].append(item)
        topics: list[dict] = []
        for topic, members in topic_groups.items():
            if len(members) < 2:
                continue
            total_access = sum(item.access_count for item in members)
            rows = []
            for item in members:
                rows.append(
                    {
                        "id": item.id,
                        "preview": item.content[:32],
                        "access_count": item.access_count,
                        "share": round(
                            item.access_count / max(1, total_access), 3
                        ),
                    }
                )
            rows.sort(key=lambda row: -row["access_count"])
            max_access = rows[0]["access_count"]
            min_access = rows[-1]["access_count"]
            imbalanced = bool(
                max_access >= ratio * max(1, min_access)
                and max_access >= 3
            )
            topics.append(
                {
                    "topic": topic,
                    "memories": rows,
                    "imbalanced": imbalanced,
                    "suggestion": (
                        "热门记忆被反复提取，兄弟记忆可能被压制："
                        "补练低频记忆，平衡提取（RIF，Anderson 1994）。"
                        if imbalanced
                        else "提取较均衡，无需调整。"
                    ),
                }
            )
        flagged = [topic for topic in topics if topic["imbalanced"]]
        if flagged:
            advice = (
                "发现提取失衡：同一主题里热门记忆反复被想起，"
                "低频记忆可能被偷偷压制，优先补练它们。"
            )
        else:
            advice = "各主题提取较均衡，无提取诱发遗忘风险。"
        return {
            "total_topics": len(topics),
            "flagged_count": len(flagged),
            "topics": topics[: max(1, int(limit))],
            "advice": advice,
        }
    def metacog_report(
        self,
        *,
        min_attempts: int = 3,
    ) -> dict:
        """Report confidence vs retrieval accuracy (calibration).

        Monitoring one's own knowledge (Koriat, 1997): good calibration
        means confidence matches accuracy. This tool aggregates retrieval
        attempts per topic, compares mean confidence with accuracy and
        flags overconfidence / underconfidence.
        """

        min_attempts = max(1, int(min_attempts))
        items = self.store.all_active()
        stats: defaultdict[str, dict] = defaultdict(
            lambda: {"attempts": 0, "successes": 0, "conf_sum": 0.0}
        )
        for item in items:
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts < min_attempts:
                continue
            topic = item.cues[0] if item.cues else item.content[:10]
            s = stats[topic]
            s["attempts"] += attempts
            s["successes"] += item.retrieval_successes
            s["conf_sum"] += item.confidence * attempts
        topics: list[dict] = []
        total_gap = 0.0
        for topic, s in stats.items():
            accuracy = round(s["successes"] / s["attempts"], 3)
            mean_confidence = round(s["conf_sum"] / s["attempts"], 3)
            gap = round(mean_confidence - accuracy, 3)
            total_gap += abs(gap)
            if gap >= 0.15:
                flag = "overconfident"
            elif gap <= -0.15:
                flag = "underconfident"
            else:
                flag = "well_calibrated"
            topics.append(
                {
                    "topic": topic,
                    "attempts": s["attempts"],
                    "accuracy": accuracy,
                    "mean_confidence": mean_confidence,
                    "gap": gap,
                    "flag": flag,
                }
            )
        topics.sort(key=lambda topic: -abs(topic["gap"]))
        mean_abs_gap = (
            round(total_gap / len(topics), 3) if topics else 0.0
        )
        calibration_score = round(
            max(0.0, min(1.0, 1.0 - mean_abs_gap)), 3
        )
        flagged = [topic for topic in topics if topic["flag"] != "well_calibrated"]
        if any(topic["flag"] == "overconfident" for topic in topics):
            advice = "存在过度自信主题：多练自测、用真实成绩校准置信度。"
        elif any(topic["flag"] == "underconfident" for topic in topics):
            advice = "存在自信不足主题：回忆成绩已不错，可适当上调置信度。"
        else:
            advice = "校准良好：置信度与真实回忆成绩基本一致。"
        return {
            "topics": topics,
            "mean_abs_gap": mean_abs_gap,
            "calibration_score": calibration_score,
            "flagged_count": len(flagged),
            "advice": advice,
        }
    def reconsolidation_plan(
        self,
        memory_id: str,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Produce an update plan for a memory that needs revision.

        Reactivated memories become labile and can be updated, not just
        replayed (Nader et al., 2000); clinical reconsolidation updating
        follows retrieve -> prediction error -> update. This tool finds
        the target memory, gathers conflicting evidence and returns a
        concrete update plan.
        """
        item = self.backend.get(memory_id)
        if item is None:
            return {
                "found": False,
                "advice": "记忆不存在：先确认 memory_id 再生成更新计划。",
            }
        item_cues = set(item.cues)
        same_topic = [
            other
            for other in self.store.all_active()
            if other.id != item.id
            and item_cues
            and (set(other.cues) & item_cues)
        ]
        conflicts = []
        for other in same_topic:
            if other.content_hash == item.content_hash:
                continue
            if len(conflicts) >= 5:
                break
            conflicts.append(
                {
                    "id": other.id,
                    "preview": other.content[:36],
                    "confidence": round(other.confidence, 3),
                }
            )
        r = self.curve.retrievability(item, now)
        steps = [
            {
                "order": 1,
                "step": "提取：先调出这条记忆，打开可更新窗口",
                "verdict": "ok",
            },
            {
                "order": 2,
                "step": "找冲突/新证据",
                "evidence_count": len(conflicts),
                "verdict": "ok" if conflicts else "weak",
            },
            {
                "order": 3,
                "step": "更新：用 update() 改写内容/置信度，或存推理记忆",
                "verdict": "ok",
            },
            {
                "order": 4,
                "step": "再巩固：更新后拉开间隔复习，避免反复提取",
                "verdict": "ok",
            },
        ]
        return {
            "found": True,
            "memory": {
                "id": item.id,
                "preview": item.content[:40],
                "confidence": round(item.confidence, 3),
                "evidence_count": item.evidence_count,
                "revision_count": item.revision_count,
                "retrievability": round(r, 3),
            },
            "related_count": len(same_topic),
            "conflicts": conflicts,
            "steps": steps,
            "advice": (
                "有冲突待更新：先提取，再按新证据改写，"
                "更新后间隔复习（Nader 2000 再巩固流程）。"
                if conflicts
                else "暂无冲突：如需刷新内容，直接 update() 后间隔复习。"
            ),
        }
    def mastery_map(
        self,
        *,
        threshold: float = 0.5,
        min_attempts: int = 3,
        now: datetime | None = None,
    ) -> dict:
        """Estimate per-topic mastery and recommend the next topic to learn.

        Zone of proximal development (Vygotsky, 1978): learning is most
        efficient just beyond current mastery. Mastery blends retrieval
        accuracy, average retrievability and topic coverage; topics in
        the "developing" band are the next-step candidates.
        """

        min_attempts = max(1, int(min_attempts))
        items = self.store.all_active()
        stats: defaultdict[str, dict] = defaultdict(
            lambda: {
                "count": 0,
                "acc_sum": 0.0,
                "r_sum": 0.0,
            }
        )
        for item in items:
            topic = item.cues[0] if item.cues else item.content[:10]
            s = stats[topic]
            s["count"] += 1
            attempts = item.retrieval_successes + item.retrieval_failures
            if attempts >= min_attempts:
                accuracy = item.retrieval_successes / attempts
            else:
                accuracy = item.confidence
            s["acc_sum"] += accuracy
            s["r_sum"] += self.curve.retrievability(item, now)
        topics: list[dict] = []
        for topic, s in stats.items():
            accuracy = s["acc_sum"] / s["count"]
            avg_r = s["r_sum"] / s["count"]
            coverage = min(1.0, s["count"] / 3.0)
            mastery = round(
                0.5 * accuracy + 0.3 * avg_r + 0.2 * coverage,
                3,
            )
            if mastery >= 0.7:
                flag = "mastered"
            elif mastery >= threshold:
                flag = "developing"
            else:
                flag = "new"
            topics.append(
                {
                    "topic": topic,
                    "memory_count": s["count"],
                    "accuracy": round(accuracy, 3),
                    "avg_retrievability": round(avg_r, 3),
                    "mastery": mastery,
                    "flag": flag,
                }
            )
        topics.sort(key=lambda topic: -topic["mastery"])
        developing = [
            topic for topic in topics if topic["flag"] == "developing"
        ]
        developing.sort(key=lambda topic: topic["mastery"])
        next_steps = [
            {"topic": topic["topic"], "mastery": topic["mastery"]}
            for topic in developing[:3]
        ]
        if next_steps:
            advice = (
                "下一步建议：先学“正在发展”的主题（最近发展区，Vygotsky 1978），"
                "从掌握度最低的开始，配合自测与间隔复习。"
            )
        else:
            advice = "没有正在发展的主题：要么都掌握（开始新主题），要么都是新主题（先建立基础）。"
        return {
            "topics": topics,
            "next_steps": next_steps,
            "advice": advice,
        }
    def attention_filter(
        self,
        task: str,
        *,
        top_k: int = 5,
        now: datetime | None = None,
    ) -> dict:
        """Filter memories for the current task (biased competition).

        Selective attention: task goals bias the competition so relevant
        representations win while distractors are suppressed (Desimone &
        Duncan, 1995). This tool recalls task-relevant memories and flags
        strong-but-irrelevant memories that should stay out of the prompt.
        """
        results = self.recall(task, top_k=max(1, int(top_k)), now=now)
        relevant = [
            {
                "id": result.item.id,
                "preview": result.item.content[:36],
                "score": round(result.score, 3),
            }
            for result in results
        ]
        relevant_ids = {item["id"] for item in relevant}
        suppressed: list[dict] = []
        for item in self.store.all_active():
            if item.id in relevant_ids:
                continue
            if item.strength >= 0.7 and item.importance >= 0.6:
                suppressed.append(
                    {
                        "id": item.id,
                        "preview": item.content[:32],
                        "strength": round(item.strength, 3),
                        "importance": round(item.importance, 3),
                        "reason": "很强但不相关：当前任务不要调出，避免分心",
                    }
                )
        suppressed.sort(
            key=lambda item: (-item["strength"], -item["importance"])
        )
        return {
            "task": task,
            "relevant": relevant,
            "kept_count": len(relevant),
            "suppressed": suppressed,
            "suppressed_count": len(suppressed),
            "advice": (
                "聚焦成功：保留相关记忆，把强但不相关的记忆挡在工作集外"
                "（偏向竞争，Desimone & Duncan 1995）。"
                if suppressed
                else "未发现强干扰记忆：按当前任务检索即可。"
            ),
        }
    def analogy_bridge(
        self,
        *,
        min_structure: float = 0.3,
        limit: int = 5,
    ) -> dict:
        """Find cross-topic memory pairs with shared structure (analogy).

        Analogical thinking maps systems of relations between different
        domains (structure-mapping; Gentner, 1983; Holyoak & Thagard,
        1995). This tool scores pairs from different topics by shared
        cues, shared terms and shared relation words, and suggests
        analogies that aid transfer.
        """


        relation_words = {
            "绕", "围绕", "大于", "小于", "等于", "导致", "因为",
            "所以", "依赖", "推动", "阻止", "包含", "属于", "对应",
            "orbit", "cause", "depend", "contain", "lead",
        }
        items = self.store.all_active()
        compare_items = random.sample(
            items, min(max(2, int(limit) * 3), 200, len(items))
        )
        rows: list[dict] = []
        for a, b in combinations(compare_items, 2):
            topic_a = a.cues[0] if a.cues else a.content[:10]
            topic_b = b.cues[0] if b.cues else b.content[:10]
            if topic_a == topic_b:
                continue
            cue_overlap = (
                len(set(a.cues) & set(b.cues))
                / max(1, len(set(a.cues) | set(b.cues)))
                if (a.cues or b.cues)
                else 0.0
            )
            terms_a = set(tokenize(a.content))
            terms_b = set(tokenize(b.content))
            term_overlap = (
                len(terms_a & terms_b) / max(1, len(terms_a | terms_b))
                if (terms_a or terms_b)
                else 0.0
            )
            relation_shared = int(
                any(word in a.content for word in relation_words)
                and any(word in b.content for word in relation_words)
            )
            structure = round(
                min(
                    1.0,
                    0.4 * cue_overlap
                    + 0.6 * term_overlap
                    + 0.2 * relation_shared,
                ),
                3,
            )
            if structure < min_structure:
                continue
            rows.append(
                {
                    "topic_a": topic_a,
                    "topic_b": topic_b,
                    "a_preview": a.content[:36],
                    "b_preview": b.content[:36],
                    "structure_score": structure,
                    "suggestion": (
                        f"结构相似：用「{topic_a}」理解「{topic_b}」，"
                        "关系可以迁移（结构映射）。"
                    ),
                }
            )
        rows.sort(key=lambda row: -row["structure_score"])
        return {
            "total_pairs_scanned": len(items) * (len(items) - 1) // 2,
            "analogy_count": len(rows),
            "analogies": rows[: max(1, int(limit))],
            "advice": (
                "找到类比桥：跨主题的结构相似记忆可以互相解释，"
                "迁移学习更省力（Gentner 1983）。"
                if rows
                else "暂无跨主题类比：继续积累不同领域记忆后再看。"
            ),
        }
    def nightly_routine(
        self,
        *,
        review_limit: int = 3,
        quiz_count: int = 3,
        now: datetime | None = None,
    ) -> dict:
        """Compose tonight's review, sleep inference and tomorrow's quiz.

        Sleep consolidates memory and pre-sleep rehearsal of important
        material strengthens it (Rasch & Born, 2013); retrieval practice
        the next day verifies and locks it in (testing effect; Roediger
        & Karpicke, 2006). This pipeline ties consolidation_forecast +
        sleep_inference + test_generator into one nightly routine.
        """
        forecast = self.consolidation_forecast(
            limit=max(1, int(review_limit)),
            now=now,
        )
        inference = self.sleep_inference(limit=1, now=now)
        quiz = self.test_generator(count=max(1, int(quiz_count)))
        tonight = [
            {
                "id": candidate["id"],
                "preview": candidate["preview"],
                "score": candidate["consolidation_score"],
            }
            for candidate in forecast["tonight_candidates"]
        ]
        return {
            "tonight_review": tonight,
            "sleep_inference_pairs": inference["ready_pairs"],
            "tomorrow_quiz": quiz["questions"],
            "advice": (
                "夜间流程：今晚复习候选 → 睡眠整合推断对 → "
                "明早自测验证（睡眠巩固 + 测试效应）。"
            ),
        }
    def cue_diversity(
        self,
        *,
        limit: int = 20,
    ) -> dict:
        """Check each memory's retrieval-cue breadth.

        Encoding specificity (Tulving & Thomson, 1973): a memory is
        reachable through cues present at encoding, and multiple distinct
        cues make retrieval more robust. Single-cue memories are fragile;
        cues shared by many memories are overloaded and weak.
        """

        items = self.store.all_active()
        cue_counts: Counter = Counter()
        for item in items:
            for cue in item.cues:
                cue_counts[cue] += 1
        rows: list[dict] = []
        for item in items:
            cue_count = len(item.cues)
            if cue_count >= 3:
                level = "robust"
            elif cue_count == 2:
                level = "ok"
            else:
                level = "fragile"
            overloaded = [
                cue for cue in item.cues if cue_counts[cue] > 4
            ]
            rows.append(
                {
                    "id": item.id,
                    "preview": item.content[:32],
                    "cue_count": cue_count,
                    "cues": item.cues[:4],
                    "level": level,
                    "overloaded_cues": overloaded[:3],
                    "suggestion": (
                        "线索太窄：加 1-2 个不同角度的线索，"
                        "检索更稳（编码特异性）。"
                        if level == "fragile" or overloaded
                        else "线索足够：保持现状。"
                    ),
                }
            )
        rows.sort(key=lambda row: row["cue_count"])
        counts = defaultdict(int)
        for row in rows:
            counts[row["level"]] += 1
        fragile = [row for row in rows if row["level"] == "fragile"]
        return {
            "total_memories": len(items),
            "level_counts": dict(counts),
            "rows": rows[: max(1, int(limit))],
            "advice": (
                "有脆弱线索：单线索/超载线索记忆容易想不起来，"
                "建议补充多角度线索（Tulving & Thomson 1973）。"
                if fragile
                else "线索结构良好：记忆检索路径丰富。"
            ),
        }
    def weekly_review(
        self,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Compose a weekly memory health review.

        Aggregates coverage (blind spots), forgetting risk, metacognitive
        calibration and tonight's consolidation candidates into one
        weekly summary plus a next-week plan.
        """
        coverage = self.coverage_report(now=now)
        risk = self.forgetting_risk(now=now, limit=5)
        meta = self.metacog_report()
        stats = self.stats()
        forecast = self.consolidation_forecast(limit=3, now=now)
        weak_topics = [
            {
                "topic": topic["topic"],
                "coverage": topic["coverage"],
                "status": topic["status"],
            }
            for topic in coverage["topics"]
            if topic["status"] in ("unreviewed", "partial")
        ]
        next_week_plan = [
            "先复习遗忘风险最高的 5 条（重要且快忘）",
            "补练未复习/只复习一半的主题（盲区）",
            "校准过度自信主题（多自测、用真实成绩对齐）",
            "每晚按夜间流程跑一遍（睡前复习 + 明早自测）",
        ]
        return {
            "week_summary": {
                "total_memories": stats["active"],
                "topics": coverage["total_topics"],
                "weak_topics": weak_topics,
                "avg_risk": risk["avg_risk"],
                "riskiest_ids": [
                    entry["id"] for entry in risk["riskiest"]
                ],
                "calibration_score": meta["calibration_score"],
                "tonight_candidates": len(forecast["tonight_candidates"]),
            },
            "next_week_plan": next_week_plan,
            "advice": (
                "周报生成：先补盲区和风险记忆，再校准置信度，"
                "每天用夜间流程巩固。"
            ),
        }
    def transfer_prompt(
        self,
        *,
        count: int = 3,
        min_mastery: float = 0.7,
        now: datetime | None = None,
    ) -> dict:
        """Generate cross-context application questions (far transfer).

        Transfer depends on applying knowledge in a new context (Barnett
        & Ceci, 2002). This tool picks mastered topics from mastery_map
        and builds hidden-answer prompts that apply the knowledge to a
        new scenario instead of re-asking the original fact.
        """
        mastery = self.mastery_map(now=now)
        mastered = [
            topic for topic in mastery["topics"]
            if topic["flag"] == "mastered"
            and topic["mastery"] >= min_mastery
        ]
        chosen = mastered[: max(1, int(count))]
        if not chosen:
            chosen = mastery["topics"][: max(1, int(count))]
        scenarios = [
            "一个陌生领域",
            "一次真实任务",
            "一个反例场景",
        ]
        prompts: list[dict] = []
        for index, topic in enumerate(chosen):
            items = [
                item
                for item in self.store.all_active()
                if item.cues and item.cues[0] == topic["topic"]
            ]
            for item in items[:1]:
                scenario = scenarios[index % len(scenarios)]
                prompts.append(
                    {
                        "memory_id": item.id,
                        "topic": topic["topic"],
                        "question": (
                            f"【迁移】把「{topic['topic']}」的知识用到"
                            f"{scenario}：说明怎么应用（答案隐藏）。"
                        ),
                        "hint_cues": item.cues[:3],
                        "answer_hidden": True,
                    }
                )
        return {
            "topics": [
                {"topic": topic["topic"], "mastery": topic["mastery"]}
                for topic in chosen
            ],
            "prompts": prompts,
            "advice": (
                "迁移题已生成：已掌握主题换新场景应用，"
                "检验的是真理解而不是死记（Barnett & Ceci 2002）。"
                if prompts
                else "暂无已掌握主题：先巩固基础，再练迁移。"
            ),
        }
    def goal_progress(
        self,
        goal: str,
        *,
        now: datetime | None = None,
    ) -> dict:
        """Measure progress toward a learning goal via topic mastery.

        Self-regulated learning requires setting goals and monitoring
        progress (Zimmerman; goal-monitoring research). This tool maps
        the goal to the best-matching topic in mastery_map and reports
        the mastery ratio and status.
        """
        mastery = self.mastery_map(now=now)
        goal_lower = goal.strip().lower()
        matches: list[dict] = []
        for topic in mastery["topics"]:
            if (
                goal_lower in topic["topic"].lower()
                or topic["topic"].lower() in goal_lower
            ):
                matches.append(topic)
        if not matches:
            for topic in mastery["topics"]:
                items = [
                    item
                    for item in self.store.all_active()
                    if item.cues and item.cues[0] == topic["topic"]
                ]
                if any(
                    goal_lower in item.content.lower()
                    for item in items
                ):
                    matches.append(topic)
        if matches:
            best = max(matches, key=lambda topic: topic["mastery"])
            progress_ratio = best["mastery"]
            if best["flag"] == "mastered":
                status = "mastered"
            elif best["flag"] == "developing":
                status = "in_progress"
            else:
                status = "not_started"
            matched_topic = best["topic"]
        else:
            progress_ratio = 0.0
            status = "not_started"
            matched_topic = None
        return {
            "goal": goal,
            "matched_topic": matched_topic,
            "progress_ratio": progress_ratio,
            "status": status,
            "advice": (
                "目标已有进度：继续按掌握度地图的下一步学，"
                "定期复查（自我调节学习）。"
                if status == "in_progress"
                else "目标已掌握：换迁移题检验真理解。"
                if status == "mastered"
                else "目标未开始：先积累该主题的基础记忆。"
            ),
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
    def timeline_report(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int = 200,
    ) -> dict:
        """Return an autobiographical timeline of episodic memories.

        Autobiographical memory is organized hierarchically by time
        (Conway & Pleydell-Pearce, 2000): life periods contain events,
        events contain details. This report lists episodic traces in
        chronological order grouped by day, optionally bounded by a
        start/end window.
        """
        items = [
            item
            for item in self.store.all_active(MemoryKind.EPISODIC)
            if item.status is MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.created_at)
        if start is not None:
            items = [item for item in items if item.created_at >= start]
        if end is not None:
            items = [item for item in items if item.created_at < end]
        items = items[: max(1, int(limit))]
        days: dict[str, list[dict]] = {}
        for item in items:
            day = item.created_at.date().isoformat()
            days.setdefault(day, []).append(
                {
                    "id": item.id,
                    "preview": item.content[:40],
                    "kind": item.kind.value,
                    "importance": round(item.importance, 3),
                    "created_at": item.created_at.isoformat(),
                }
            )
        out = [
            {"date": day, "count": len(entries), "items": entries}
            for day, entries in sorted(days.items())
        ]
        return {
            "total": len(items),
            "days": out,
            "start_date": out[0]["date"] if out else None,
            "end_date": out[-1]["date"] if out else None,
        }
    def recognition_check(
        self,
        query: str,
        memory_id: str,
    ) -> dict:
        """Classify a memory hit as recollection vs familiarity.

        Dual-process theory (Yonelinas, 2002): recognition can rest on
        recollection (specific evidence recovered) or familiarity (a
        vague "I know it" without detail). This tool checks one candidate
        memory against a query and reports which process supports it.
        """

        item = self.backend.get(memory_id)
        if item is None:
            return {"memory_id": memory_id, "verdict": "missing"}
        results = self.recall(query, top_k=10)
        entry = next(
            (r for r in results if r.item.id == memory_id), None
        )
        q_terms = set(tokenize(query))
        item_terms = set(tokenize(item.content)) | set(item.cues)
        common = len(q_terms & item_terms)
        overlap = (
            common / max(1, min(len(q_terms), len(item_terms)))
            if q_terms and item_terms
            else 0.0
        )
        if entry is None:
            verdict = "unmatched"
            score = 0.0
            reasons = []
        else:
            score = entry.score
            reasons = entry.reasons
            evidence = any(
                "overlap" in r or "semantic" in r for r in reasons
            )
            if overlap >= 0.6:
                verdict = "recollection"
            elif overlap > 0 and evidence:
                verdict = "familiarity"
            else:
                verdict = "unmatched"
        return {
            "memory_id": memory_id,
            "verdict": verdict,
            "score": round(score, 3),
            "overlap": round(overlap, 3),
            "confidence": item.confidence,
            "reasons": reasons[:5],
        }

    def conflict_advice(
        self,
        now: datetime | None = None,
        limit: int = 10,
    ) -> dict:
        """Give resolution advice for each detected memory conflict.

        Every contradiction is scored on both sides by evidence count,
        confidence, importance, access history, source trust and recency.
        The report says which side is stronger, or asks the user to clarify
        when the two sides are too close to call.
        """
        now = now or utcnow()
        conflicts = self.consolidator.detect_conflicts()
        rows: list[dict] = []

        def _score(item: MemoryItem) -> float:
            recency_hours = max(
                0.0,
                (
                    now - (item.updated_at or item.created_at)
                ).total_seconds()
                / 3600.0,
            )
            recency = 1.0 / (1.0 + recency_hours / 168.0)
            return (
                item.evidence_count * 2.0
                + item.confidence
                + item.importance
                + min(item.access_count, 5) * 0.2
                + item.source.trust
                + recency
            )

        for conflict in conflicts[: max(1, int(limit))]:
            a, b = conflict.a, conflict.b
            score_a, score_b = _score(a), _score(b)
            gap = abs(score_a - score_b) / max(1.0, max(score_a, score_b))
            if gap < 0.08:
                verdict = "clarify"
                advice = (
                    "两边证据接近，建议向用户确认后保留正确的一方，"
                    "并删除或修正另一方。"
                )
            else:
                winner, loser = (a, b) if score_a > score_b else (b, a)
                verdict = "prefer_a" if winner is a else "prefer_b"
                advice = (
                    f"证据对比后建议以“{winner.content[:32]}”为准"
                    f"（证据{winner.evidence_count}条、"
                    f"置信度{winner.confidence:.2f}），"
                    f"复查并修正“{loser.content[:32]}”。"
                )
            rows.append(
                {
                    "id_a": a.id,
                    "content_a": a.content[:80],
                    "id_b": b.id,
                    "content_b": b.content[:80],
                    "reason": conflict.reason,
                    "score_a": round(score_a, 3),
                    "score_b": round(score_b, 3),
                    "verdict": verdict,
                    "advice": advice,
                }
            )
        return {"conflicts": len(conflicts), "advice": rows}

    def interference_report(
        self,
        shared_cue_min: int = 3,
        limit: int = 20,
    ) -> dict:
        """Report cue-crowded clusters that cause interference.

        Proactive interference (Wickens, 1972): when too many memories
        hang on the same cue, they compete and get confused. This tool
        finds cues with >= shared_cue_min active memories and suggests
        differentiating them with extra cues.
        """

        cue_members: dict[str, list] = defaultdict(list)
        for item in self.store.all_active():
            for cue in item.cues:
                cue_members[cue].append(item)
        clusters = []
        for cue, members in cue_members.items():
            if len(members) < max(2, int(shared_cue_min)):
                continue
            total_overlap = 0.0
            pairs = 0
            for i in range(len(members)):
                a_terms = set(tokenize(members[i].content))
                for j in range(i + 1, len(members)):
                    b_terms = set(tokenize(members[j].content))
                    common = len(a_terms & b_terms)
                    denominator = max(
                        1, min(len(a_terms), len(b_terms))
                    )
                    total_overlap += common / denominator
                    pairs += 1
            avg_overlap = (
                round(total_overlap / pairs, 3) if pairs else 0.0
            )
            members.sort(key=lambda it: it.seq, reverse=True)
            clusters.append(
                {
                    "cue": cue,
                    "memory_count": len(members),
                    "avg_content_overlap": avg_overlap,
                    "members": [
                        {
                            "id": item.id,
                            "preview": item.content[:32],
                        }
                        for item in members[:5]
                    ],
                }
            )
        clusters.sort(
            key=lambda c: (-c["memory_count"], c["cue"])
        )
        clusters = clusters[: max(1, int(limit))]
        return {
            "total_cues": len(cue_members),
            "crowded_clusters": clusters,
            "suggestion": (
                "给同一线索下的记忆补上区别性线索（日期/对象/主题词），"
                "降低互相抢答"
            ),
        }
    def life_story(
        self,
        period_days: int = 30,
        limit: int = 20,
    ) -> dict:
        """Summarize the memory store as life periods.

        Autobiographical memory is organized into lifetime periods that
        contain events (Conway & Pleydell-Pearce, 2000). This tool groups
        episodic traces into time buckets (default 30 days) and reports
        each period's event count, top themes, average importance and
        highlights.
        """

        epoch = date(1970, 1, 1)
        items = [
            item
            for item in self.store.all_active(MemoryKind.EPISODIC)
            if item.status is MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.created_at)
        buckets: dict[date, list] = defaultdict(list)
        for item in items:
            day = item.created_at.date()
            bucket = epoch + timedelta(
                days=(day - epoch).days // max(1, int(period_days))
                * max(1, int(period_days))
            )
            buckets[bucket].append(item)
        periods = []
        for bucket in sorted(buckets):
            members = buckets[bucket]
            theme_counts: dict[str, int] = defaultdict(int)
            importance_sum = 0.0
            for item in members:
                topic = item.cues[0] if item.cues else "（无标签）"
                theme_counts[topic] += 1
                importance_sum += item.importance
            highlights = sorted(
                members,
                key=lambda it: (it.importance, it.seq),
                reverse=True,
            )[:3]
            periods.append(
                {
                    "period_start": bucket.isoformat(),
                    "period_end": (
                        bucket + timedelta(days=max(1, int(period_days)) - 1)
                    ).isoformat(),
                    "event_count": len(members),
                    "top_themes": [
                        {"cue": cue, "count": count}
                        for cue, count in sorted(
                            theme_counts.items(),
                            key=lambda kv: (-kv[1], kv[0]),
                        )[:5]
                    ],
                    "avg_importance": round(
                        importance_sum / len(members), 3
                    ),
                    "highlights": [
                        {
                            "id": item.id,
                            "preview": item.content[:32],
                            "importance": round(item.importance, 3),
                        }
                        for item in highlights
                    ],
                }
            )
        periods = periods[: max(1, int(limit))]
        return {
            "period_days": max(1, int(period_days)),
            "total_events": len(items),
            "periods": periods,
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
