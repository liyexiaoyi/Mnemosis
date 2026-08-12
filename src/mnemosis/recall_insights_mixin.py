"""Recall insights mixin: reasoning pack, step retrieval, review consistency, similarity and association reports."""

from __future__ import annotations

import re
from datetime import datetime

from .reasoning import suggested_pack_size
from .types import MemoryKind, RecallResult, tokenize, utcnow
from .zh_nlp import expand_synonyms


class RecallInsightsMixin:
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
