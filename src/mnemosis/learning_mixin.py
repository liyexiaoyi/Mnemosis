"""Learning analysis mixin: agent learning loops and session scoring."""

from __future__ import annotations

from datetime import datetime


class LearningSessionMixin:
    def learning_loop(
        self,
        *,
        now: datetime | None = None,
        count: int = 1,
    ) -> dict:
        """Build a ready-to-run learning loop: review -> practice -> snapshot.

        Combines three evidence-backed principles into one agent-facing
        loop: spaced-review adherence (Cepeda et al., 2006), the testing
        effect (Roediger & Karpicke, 2006) and longitudinal knowledge
        tracking (retrieval_snapshot). The returned steps say what to
        review first, which self-test question to attempt for the
        weakest topic, and which snapshot to take afterwards to measure
        progress. Read-only.
        """
        baseline = self.retrieval_snapshot(now=now)
        consistency = self.review_consistency(now=now)
        mastery = self.mastery_map(now=now)
        focus = None
        if mastery["next_steps"]:
            focus = mastery["next_steps"][0]["topic"]
        elif mastery["topics"]:
            focus = mastery["topics"][0]["topic"]
        practice = None
        if focus:
            mastered = any(
                entry["topic"] == focus and entry["flag"] == "mastered"
                for entry in mastery["topics"]
            )
            if mastered:
                generated = self.analogy_prompt(
                    topic=focus, count=max(1, int(count))
                )
                practice = {
                    "kind": "analogy",
                    "topic": focus,
                    "questions": generated["prompts"][
                        : max(1, int(count))
                    ],
                }
            else:
                generated = self.test_generator(
                    topic=focus, count=max(1, int(count))
                )
                practice = {
                    "kind": "test",
                    "topic": focus,
                    "questions": generated["questions"][
                        : max(1, int(count))
                    ],
                }
        if practice and practice["questions"]:
            practice_question = practice["questions"][0]["question"]
        else:
            practice_question = "记忆库里还没有可练的题，先积累内容。"
        steps = [
            {
                "order": 1,
                "step": "清积压",
                "detail": (
                    f"先复习 {consistency['overdue_count']} 条过期记忆；"
                    "从最重要+最晚到期的开始。"
                ),
            },
            {
                "order": 2,
                "step": "做练习",
                "detail": practice_question,
            },
            {
                "order": 3,
                "step": "拍快照",
                "detail": (
                    "学完后再拍一张记忆快照，对比本次 baseline"
                    "看进步/退步。"
                ),
            },
        ]
        verdict = "empty" if not mastery["topics"] else "ready"
        if verdict == "empty":
            advice = (
                "记忆库还是空的：先存入学习内容，才能形成"
                "复习→练习→快照的闭环。"
            )
        else:
            advice = (
                f"学习闭环已生成：先清 {consistency['overdue_count']} 条"
                "积压，再做练习，最后拍快照对比——按顺序执行就能看到进步。"
            )
        return {
            "baseline": baseline["snapshot"],
            "review": {
                "overdue_count": consistency["overdue_count"],
                "never_reviewed_count": consistency["never_reviewed_count"],
                "adherence_ratio": consistency["adherence_ratio"],
            },
            "focus_topic": focus,
            "practice": practice,
            "steps": steps,
            "verdict": verdict,
            "advice": advice,
        }

    def agent_learning_session(
        self,
        answers: list[dict] | None = None,
        *,
        now: datetime | None = None,
        count: int = 1,
    ) -> dict:
        """Run one end-to-end agent learning session (study + measure + plan).

        Executes the learning loop with real scoring: each attempt goes
        through practice_answer (testing effect; Roediger & Karpicke,
        2006), review consistency is re-checked, a second snapshot is
        diffed against the baseline (knowledge tracing), and the next
        loop is planned. Answers are ``{"id": memory_id, "attempt": str}``.
        """
        loop = self.learning_loop(now=now, count=count)
        baseline = loop["baseline"]
        scored: list[dict] = []
        if answers:
            for entry in answers:
                try:
                    result = self.practice_answer(
                        entry["id"],
                        entry.get("attempt", ""),
                        now=now,
                    )
                    scored.append(
                        {
                            "memory_id": entry["id"],
                            "success": bool(result["success"]),
                            "retrievability_after": result["retrievability"],
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    scored.append(
                        {
                            "memory_id": entry.get("id"),
                            "success": False,
                            "error": str(exc)[:40],
                        }
                    )
        after = self.retrieval_snapshot(
            previous={"snapshot": baseline}, now=now
        )
        consistency = self.review_consistency(now=now)
        next_loop = self.learning_loop(now=now, count=count)
        attempted = len(scored)
        correct = sum(1 for item in scored if item["success"])
        verdict = "empty" if not loop["practice"] else "ready"
        if verdict == "empty":
            advice = (
                "记忆库还是空的：先存入学习内容，再开学习会话。"
            )
        elif attempted:
            advice = (
                f"本次答对 {correct}/{attempted}，"
                f"快照结论：{after['diff']['verdict']}。"
                "下一轮计划已生成，按顺序继续。"
            )
        else:
            advice = (
                "本次没有答题记录：先做练习，再回来拍快照对比。"
            )
        return {
            "baseline": baseline,
            "practice": loop["practice"],
            "scored": scored,
            "session_result": {
                "attempted": attempted,
                "correct": correct,
                "success_rate": (
                    round(correct / max(1, attempted), 3)
                    if attempted
                    else None
                ),
            },
            "snapshot_after": {
                "diff": after["diff"],
                "advice": after["advice"],
            },
            "review_after": {
                "overdue_count": consistency["overdue_count"],
                "adherence_ratio": consistency["adherence_ratio"],
            },
            "next_loop": {
                "focus_topic": next_loop["focus_topic"],
                "steps": next_loop["steps"],
                "verdict": next_loop["verdict"],
            },
            "verdict": verdict,
            "advice": advice,
        }


__all__ = ["LearningSessionMixin"]
