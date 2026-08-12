"""Practice mixin: mastery estimation and retrieval-practice generation."""
# mypy: disable-error-code="attr-defined"

from __future__ import annotations

from collections import defaultdict
from datetime import datetime


class PracticeMixin:
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


__all__ = ["PracticeMixin"]
