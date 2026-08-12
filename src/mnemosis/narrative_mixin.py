"""Narrative mixin: timeline, recognition, conflict and life-story reports."""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta

from .types import MemoryItem, MemoryKind, MemoryStatus, tokenize, utcnow


class NarrativeMixin:
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



__all__ = ["NarrativeMixin"]
