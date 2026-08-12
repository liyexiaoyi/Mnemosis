"""Overview mixin: memory health, map, KG export, learner profile, context pack, encoding quality."""

from __future__ import annotations

from datetime import datetime

from .types import MemoryItem, utcnow


class OverviewMixin:
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
