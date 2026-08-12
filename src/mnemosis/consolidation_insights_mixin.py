"""Consolidation insights mixin: forgetting, consolidation and metacognition reports."""
# mypy: disable-error-code="attr-defined"

from __future__ import annotations

from collections import defaultdict
from datetime import datetime


class ConsolidationInsightsMixin:
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
        conflicts: list[dict] = []
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



__all__ = ["ConsolidationInsightsMixin"]
