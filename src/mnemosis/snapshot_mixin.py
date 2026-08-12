"""Snapshot mixin: memory-state snapshots and retrieval assistance."""
# mypy: disable-error-code="attr-defined"

from __future__ import annotations

from datetime import datetime

from .types import tokenize, utcnow
from .zh_nlp import expand_synonyms, has_cjk


class SnapshotMixin:
    def retrieval_snapshot(
        self,
        *,
        previous: dict | None = None,
        now: datetime | None = None,
    ) -> dict:
        """Capture a compact memory-state snapshot (longitudinal tracking).

        Knowledge tracing monitors how a learner's knowledge state
        evolves over time (knowledge-tracing literature). This captures
        key indicators; passing a previous snapshot adds a progress diff.
        """
        stats = self.stats()
        items = self.store.all_active()
        avg_r = round(
            sum(self.curve.retrievability(item, now) for item in items)
            / max(1, len(items)),
            3,
        )
        reviewed = sum(
            1
            for item in items
            if item.retrieval_successes + item.retrieval_failures > 0
        )
        risk = self.forgetting_risk(now=now)
        meta = self.metacog_report()
        snapshot = {
            "total_memories": stats["active"],
            "avg_retrievability": avg_r,
            "reviewed_ratio": round(reviewed / max(1, len(items)), 3),
            "avg_risk": risk["avg_risk"],
            "calibration_score": meta["calibration_score"],
            "topics": len(meta["topics"]),
        }
        diff: dict | None = None
        if previous and previous.get("snapshot"):
            prev = previous["snapshot"]
            diff = {}
            for key, value in snapshot.items():
                if key in prev:
                    diff[key] = round(value - prev[key], 3)
            progress = sum(
                1
                for key in (
                    "avg_retrievability", "reviewed_ratio",
                    "calibration_score",
                )
                if diff.get(key, 0) > 0
            )
            regress = sum(
                1
                for key in (
                    "avg_retrievability", "reviewed_ratio",
                    "calibration_score",
                )
                if diff.get(key, 0) < 0
            )
            verdict = "improving" if progress > regress else (
                "declining" if regress > progress else "stable"
            )
            diff["verdict"] = verdict
        return {
            "captured_at": (now or utcnow()).isoformat(),
            "snapshot": snapshot,
            "diff": diff,
            "advice": (
                "快照已生成：下次再拍一张对比，就能看到进步/退步"
                "（知识追踪，纵向监控）。"
                if diff is None
                else f"快照对比完成：{diff.get('verdict', 'stable')}。"
            ),
        }

    def retrieval_assist(
        self,
        query: str,
        *,
        limit: int = 8,
        now: datetime | None = None,
    ) -> dict:
        """Suggest alternative retrieval cues when a query stalls.

        Encoding specificity (Tulving & Thomson, 1973) and
        transfer-appropriate processing (Morris, Bransford & Franks,
        1977): a memory is reachable through the cues present at encoding,
        so rephrasing the question with the stored cue words recovers
        traces the original query misses. This tool mines existing cues
        and content terms that overlap the (synonym-expanded) query and
        returns them as concrete follow-up queries.
        """

        q_terms = set(tokenize(query))
        expanded = (
            expand_synonyms(q_terms) if has_cjk(query) else set(q_terms)
        )
        new_synonyms = sorted(expanded - q_terms)
        cue_counts: dict[str, int] = {}
        content_counts: dict[str, int] = {}
        for item in self.store.all_active():
            best_cue = 0
            for cue in item.cues:
                common = len(expanded & set(tokenize(cue)))
                best_cue = max(best_cue, common)
            if best_cue and item.cues:
                cue_counts[item.cues[0]] = max(
                    cue_counts.get(item.cues[0], 0), best_cue
                )
            common = len(expanded & set(tokenize(item.content)))
            if common:
                for cue in item.cues[:3] or [item.content[:12]]:
                    content_counts[cue] = max(
                        content_counts.get(cue, 0), common
                    )
        suggestions: list[dict] = []
        for cue, count in sorted(
            cue_counts.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            suggestions.append(
                {"cue": cue, "source": "cue", "matched_count": count}
            )
        for cue, count in sorted(
            content_counts.items(), key=lambda kv: (-kv[1], kv[0])
        ):
            if not any(s["cue"] == cue for s in suggestions):
                suggestions.append(
                    {
                        "cue": cue,
                        "source": "content",
                        "matched_count": count,
                    }
                )
        suggestions = suggestions[: max(1, int(limit))]
        recall = self.recall(query, top_k=3, now=now)
        return {
            "query": query,
            "expanded_terms": sorted(expanded),
            "new_synonyms": new_synonyms,
            "suggestions": suggestions,
            "top_recall": [
                {
                    "id": r.item.id,
                    "preview": r.item.content[:40],
                    "score": round(r.score, 3),
                    "confident": r.confident,
                }
                for r in recall
            ],
        }


__all__ = ["SnapshotMixin"]
