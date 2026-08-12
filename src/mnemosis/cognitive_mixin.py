"""Cognitive mixin: rumination, attention, analogy, routine and goal-progress tools."""
# mypy: disable-error-code="attr-defined"

from __future__ import annotations

import random
from collections import Counter, defaultdict
from datetime import datetime
from itertools import combinations

from .types import tokenize


class CognitiveMixin:
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
        rumination_topics: list[dict] = [
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
        counts: defaultdict[str, int] = defaultdict(int)
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



__all__ = ["CognitiveMixin"]
