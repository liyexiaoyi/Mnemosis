"""Agent project layer tests (round 36: planning / outcomes / MCP tools).

Human principles: prefrontal goal maintenance (Miller & Cohen, 2001),
analogical transfer (Gick & Holyoak, 1980), outcome monitoring and evidence
accumulation (Smolen et al., 2016).
"""

from __future__ import annotations

import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _project_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    steps = [
        ("阿丽在2026年4月1日订了去京都的机票。", "阿丽", "2026-04-01"),
        ("阿丽在2026年4月2日买了相机。", "阿丽", "2026-04-02"),
        ("阿丽在2026年4月3日收拾了行李。", "阿丽", "2026-04-03"),
        ("阿丽在2026年4月4日去了京都。", "阿丽", "2026-04-04"),
    ]
    for content, person, iso in steps:
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, iso],
        )
    return engine


class AgentPlanningTests(unittest.TestCase):
    def test_plan_for_goal_reuses_reference_steps_in_order(self) -> None:
        engine = _project_engine()
        plan = engine.plan_for_goal(
            "大壮想去京都旅行，参考阿丽是怎么准备的？", top_k=8
        )
        contents = [r.item.content for r in plan]
        self.assertEqual(
            contents[0],
            "阿丽在2026年4月1日订了去京都的机票。",
        )
        self.assertEqual(
            contents[3],
            "阿丽在2026年4月4日去了京都。",
        )
        self.assertTrue(
            any(
                "\u7c7b\u6bd4\u8ba1\u5212" in reason
                for r in plan
                for reason in r.reasons
            )
        )

    def test_record_outcome_is_retrievable(self) -> None:
        engine = _project_engine()
        engine.record_outcome(
            "去京都旅行", "订机票", success=False, note="航班取消"
        )
        results = engine.recall("去京都旅行 订机票 执行结果", top_k=3)
        self.assertTrue(
            any("失败" in r.item.content for r in results)
        )


class MCPAgentToolTests(unittest.TestCase):
    def test_plan_tool(self) -> None:
        server = MCPServer(engine=_project_engine())
        result = server._call_tool("plan", {"goal": "大壮想去京都旅行，参考阿丽"})
        self.assertEqual(result[0]["content"], "阿丽在2026年4月1日订了去京都的机票。")

    def test_reason_tool(self) -> None:
        server = MCPServer(engine=MemoryEngine())
        server.engine.remember(
            "阿丽买相机花了2500元。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽"],
        )
        result = server._call_tool("reason", {"query": "阿丽的相机多少钱？"})
        self.assertTrue(any("2500" in r["content"] for r in result))

    def test_record_outcome_tool(self) -> None:
        server = MCPServer(engine=MemoryEngine())
        result = server._call_tool(
            "record_outcome",
            {"goal": "搬家", "step": "打包箱子", "success": True},
        )
        self.assertIn("成功", result["content"])


class OutcomeAwarePlanningTests(unittest.TestCase):
    def _engine(self) -> MemoryEngine:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        for content, person, iso in (
            ("阿丽在2026年4月1日订了去京都的机票。", "阿丽", "2026-04-01"),
            ("阿丽在2026年4月2日买了相机。", "阿丽", "2026-04-02"),
            ("小波在2026年5月1日订了去京都的机票。", "小波", "2026-05-01"),
            ("小波在2026年5月2日买了相机。", "小波", "2026-05-02"),
        ):
            engine.remember(
                content,
                kind=MemoryKind.EPISODIC,
                source=source,
                cues=[person, iso],
            )
        # 阿丽's 订机票 failed twice; 小波's steps all succeeded
        engine.record_outcome("阿丽旅行", "订机票", success=False,
                              note="航班取消")
        engine.record_outcome("阿丽旅行", "订机票", success=False,
                              note="再次取消")
        engine.record_outcome("小波旅行", "订机票", success=True)
        engine.record_outcome("小波旅行", "买相机", success=True)
        return engine

    def test_successful_plan_ranks_first(self) -> None:
        engine = self._engine()
        plan = engine.plan_for_goal(
            "大壮想去京都旅行，参考阿丽和小波谁的计划更好？",
            top_k=8,
            outcome_aware=True,
        )
        contents = [r.item.content for r in plan]
        self.assertTrue(
            contents.index("小波在2026年5月1日订了去京都的机票。")
            < contents.index("阿丽在2026年4月1日订了去京都的机票。")
        )
        # failed step demoted and marked
        failed_step = next(
            r for r in plan
            if r.item.content.startswith("阿丽在2026年4月1日")
        )
        self.assertTrue(
            any("\u7ed3\u679c\u52a0\u6743" in reason
                for reason in failed_step.reasons)
        )

    def test_outcome_aware_off_keeps_chronology(self) -> None:
        engine = self._engine()
        plan = engine.plan_for_goal(
            "大壮想去京都旅行，参考阿丽和小波谁的计划更好？",
            top_k=8,
            outcome_aware=False,
        )
        contents = [r.item.content for r in plan]
        self.assertEqual(
            contents[0],
            "阿丽在2026年4月1日订了去京都的机票。",
        )

    def test_mcp_plan_tool_uses_outcome_rerank(self) -> None:
        server = MCPServer(engine=self._engine())
        result = server._call_tool(
            "plan",
            {"goal": "大壮想去京都旅行，参考阿丽和小波谁的计划更好？",
             "top_k": 8},
        )
        contents = [r["content"] for r in result]
        self.assertTrue(
            contents.index("小波在2026年5月1日订了去京都的机票。")
            < contents.index("阿丽在2026年4月1日订了去京都的机票。")
        )
        self.assertTrue(
            any(
                "\u7ed3\u679c\u52a0\u6743" in reason
                for r in result
                for reason in r["reasons"]
            )
        )

    def test_suggested_plan_size(self) -> None:
        engine = MemoryEngine()
        self.assertEqual(engine._suggested_plan_size("大壮想去京都旅行"), 8)
        self.assertEqual(
            engine._suggested_plan_size("大壮想去京都旅行，参考阿丽"), 8
        )
        self.assertEqual(
            engine._suggested_plan_size(
                "大壮想去京都旅行，参考阿丽和小波"
            ),
            10,
        )
        self.assertEqual(
            engine._suggested_plan_size(
                "大壮想去京都旅行，参考阿丽和小波，把完整计划按顺序列出"
            ),
            12,
        )

    def test_auto_capacity_keeps_full_plan(self) -> None:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        steps = [
            ("阿丽在2026年4月1日订了去京都的机票。", "2026-04-01"),
            ("阿丽在2026年4月2日买了相机。", "2026-04-02"),
            ("阿丽在2026年4月3日收拾了行李。", "2026-04-03"),
            ("阿丽在2026年4月4日订了酒店。", "2026-04-04"),
            ("阿丽在2026年4月5日去了京都。", "2026-04-05"),
        ]
        for content, iso in steps:
            engine.remember(
                content,
                kind=MemoryKind.EPISODIC,
                source=source,
                cues=["阿丽", iso],
            )
        auto = engine.plan_for_goal(
            "大壮想去京都旅行，参考阿丽，把完整计划按顺序列出",
            outcome_aware=False,
        )
        contents = [r.item.content for r in auto]
        self.assertTrue(all(s in contents for s, _ in steps))

    def test_plan_effort_levels(self) -> None:
        engine = MemoryEngine()
        self.assertEqual(engine._plan_effort("阿丽喜欢什么颜色？"), "low")
        self.assertEqual(engine._plan_effort("大壮想去京都旅行"), "low")
        self.assertEqual(
            engine._plan_effort("大壮想去京都旅行，参考阿丽"), "medium"
        )
        self.assertEqual(
            engine._plan_effort(
                "大壮想去京都旅行，参考阿丽和小波，预算5000，3个人，按顺序列出"
            ),
            "high",
        )

    def test_low_effort_skips_outcome_rerank(self) -> None:
        engine = self._engine()
        low = engine.plan_for_goal(
            "大壮想去京都旅行",
            outcome_aware=True,  # explicit True must be overridden by effort
        )
        contents = [r.item.content for r in low]
        self.assertTrue(
            contents.index("阿丽在2026年4月1日订了去京都的机票。")
            < contents.index("小波在2026年5月1日订了去京都的机票。")
        )
        self.assertFalse(
            any(
                "\u7ed3\u679c\u52a0\u6743" in reason
                for r in low
                for reason in r.reasons
            )
        )

    def test_mcp_plan_effort_param(self) -> None:
        server = MCPServer(engine=self._engine())
        low = server._call_tool(
            "plan",
            {"goal": "大壮想去京都旅行，参考阿丽和小波",
             "effort": "low"},
        )
        self.assertFalse(
            any(
                "\u7ed3\u679c\u52a0\u6743" in reason
                for r in low
                for reason in r["reasons"]
            )
        )
        high = server._call_tool(
            "plan",
            {"goal": "大壮想去京都旅行，参考阿丽和小波",
             "effort": "high"},
        )
        self.assertTrue(
            any(
                "\u7ed3\u679c\u52a0\u6743" in reason
                for r in high
                for reason in r["reasons"]
            )
        )

    def test_replan_avoids_failed_step_and_records_decision(self) -> None:
        engine = self._engine()
        plan = engine.replan(
            "大壮想去京都旅行，参考阿丽和小波",
            "订机票",
        )
        contents = [r.item.content for r in plan]
        failed_steps = [c for c in contents if c.startswith("阿丽")]
        failed_flight = [c for c in failed_steps if "机票" in c]
        others = [
            c for c in contents
            if not (c.startswith("阿丽") and "机票" in c)
        ]
        # only 阿丽's failed flight step is moved to the end
        self.assertTrue(others)
        self.assertTrue(failed_flight)
        self.assertTrue(
            any("小波在2026年5月1日订了去京都的机票。" in c
                for c in others)
        )
        self.assertEqual(
            contents[: len(others)],
            others,
        )
        for r in plan:
            if r.item.content.startswith("阿丽") and "机票" in r.item.content:
                self.assertTrue(
                    any("\u91cd\u89c4\u5212" in reason
                        for reason in r.reasons)
                )
        # re-planning decision is stored and retrievable
        recall = engine.recall("重新规划 订机票", top_k=3)
        self.assertTrue(
            any("\u91cd\u65b0\u89c4\u5212" in r.item.content
                for r in recall)
        )

    def test_mcp_replan_tool(self) -> None:
        server = MCPServer(engine=self._engine())
        result = server._call_tool(
            "replan",
            {"goal": "大壮想去京都旅行，参考阿丽和小波",
             "failed_step": "订机票"},
        )
        contents = [r["content"] for r in result]
        self.assertEqual(
            contents[-1],
            "阿丽在2026年4月1日订了去京都的机票。",
        )
        self.assertTrue(
            any(
                "\u91cd\u89c4\u5212" in reason
                for r in result
                for reason in r["reasons"]
            )
        )

    def test_prediction_error_updates(self) -> None:
        engine = MemoryEngine()
        for _ in range(5):
            engine.record_outcome("旅行", "订机票", success=True)
        self.assertEqual(
            engine.predict_step("订机票")["success_probability"], 1.0
        )
        surprising = engine.record_outcome(
            "旅行", "订机票", success=False, note="航班取消"
        )
        self.assertGreaterEqual(surprising.importance, 0.85)
        self.assertIn("\u610f\u5916", surprising.cues)
        self.assertAlmostEqual(
            engine.predict_step("订机票")["success_probability"],
            5 / 6,
            places=3,
        )
        expected = engine.record_outcome("旅行", "订机票", success=True)
        self.assertLess(expected.importance, surprising.importance)
        self.assertNotIn("\u610f\u5916", expected.cues)

    def test_predict_step_unknown_is_uncertain(self) -> None:
        engine = MemoryEngine()
        pred = engine.predict_step("买相机")
        self.assertEqual(pred["success_probability"], 0.5)
        self.assertEqual(pred["confidence"], 0.0)

    def test_mcp_predict_step_tool(self) -> None:
        engine = MemoryEngine()
        for _ in range(3):
            engine.record_outcome("旅行", "订机票", success=True)
        server = MCPServer(engine=engine)
        result = server._call_tool("predict_step", {"step": "订机票"})
        self.assertEqual(result["success_probability"], 1.0)

    def test_sleep_replay_consolidates_and_strengthens(self) -> None:
        engine = MemoryEngine()
        for _ in range(5):
            engine.record_outcome("旅行", "订机票", success=True)
        surprising = engine.record_outcome(
            "旅行", "订机票", success=False, note="航班取消"
        )
        retrieval_before = surprising.retrieval_successes
        for _ in range(3):
            engine.record_outcome("旅行", "买相机", success=True)
        report = engine.sleep_replay()
        self.assertEqual(report["replayed_surprising"], 1)
        self.assertEqual(report["consolidated_steps"], 2)
        self.assertGreater(surprising.retrieval_successes, retrieval_before)
        pred = engine.predict_step("订机票")
        self.assertEqual(pred["source"], "consolidated")
        self.assertAlmostEqual(
            pred["success_probability"], 5 / 6, places=3
        )
        summary = engine.recall("订机票 历史成功率", top_k=3)
        self.assertTrue(
            any("历史成功率" in r.item.content for r in summary)
        )

    def test_mcp_sleep_replay_tool(self) -> None:
        engine = MemoryEngine()
        for _ in range(3):
            engine.record_outcome("旅行", "订机票", success=True)
        engine.record_outcome("旅行", "订机票", success=False, note="航班取消")
        server = MCPServer(engine=engine)
        result = server._call_tool("sleep_replay", {})
        self.assertEqual(result["replayed_surprising"], 1)
        self.assertEqual(result["consolidated_steps"], 1)

    def test_mcp_review_due_desirable(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        for i, strength in enumerate((0.5, 0.5, 0.5)):
            engine.remember(
                f"待复习{i}",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"r{i}"],
                strength=strength,
                created_at=now - timedelta(days=(5 + i * 10)),
            )
        server = MCPServer(engine=engine)
        plain = server._call_tool("review_due", {"limit": 3})
        desirable = server._call_tool(
            "review_due", {"limit": 3, "desirable_difficulty": True}
        )
        self.assertNotEqual(
            [r["content"] for r in plain],
            [r["content"] for r in desirable],
        )

    def test_practice_loop(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        item = engine.remember(
            "阿丽最喜欢的颜色是琥珀色。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "颜色"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        due = engine.practice_due(limit=5, now=now)
        self.assertTrue(any(d["id"] == item.id for d in due))
        self.assertNotIn("琥珀色", str([d["cue"] for d in due]))
        wrong = engine.practice_answer(item.id, "红色", now=now)
        self.assertFalse(wrong["success"])
        right = engine.practice_answer(item.id, "琥珀色", now=now)
        self.assertTrue(right["success"])
        self.assertEqual(right["content"], item.content)

    def test_mcp_practice_tools(self) -> None:
        engine = MemoryEngine()
        engine.remember(
            "阿丽喜欢的食物是饺子。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "食物"],
            importance=0.8,
            strength=0.5,
            created_at=utcnow() - timedelta(days=20),
        )
        server = MCPServer(engine=engine)
        due = server._call_tool("practice_due", {"limit": 5})
        self.assertTrue(due)
        result = server._call_tool(
            "practice_answer",
            {"memory_id": due[0]["id"], "attempt": "饺子"},
        )
        self.assertTrue(result["success"])

    def test_practice_report(self) -> None:
        engine = MemoryEngine()
        item = engine.remember(
            "阿丽喜欢的城市是成都。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "城市"],
            importance=0.8,
            strength=0.5,
            created_at=utcnow() - timedelta(days=20),
        )
        report = engine.practice_report(
            [
                {"id": item.id, "attempt": "成都"},
                {"id": item.id, "attempt": "错误"},
            ]
        )
        self.assertEqual(report["successes"], 1)
        self.assertEqual(report["failures"], 1)
        self.assertEqual(report["success_rate"], 0.5)

    def test_mcp_practice_report_tool(self) -> None:
        engine = MemoryEngine()
        item = engine.remember(
            "阿丽喜欢的运动是游泳。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "运动"],
            importance=0.8,
            strength=0.5,
            created_at=utcnow() - timedelta(days=20),
        )
        server = MCPServer(engine=engine)
        result = server._call_tool(
            "practice_report",
            {"answers": [{"id": item.id, "attempt": "游泳"}]},
        )
        self.assertEqual(result["successes"], 1)

    def test_practice_due_spacing_gap(self) -> None:
        engine = MemoryEngine()
        now = utcnow()
        item = engine.remember(
            "阿丽喜欢的季节是春天。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "季节"],
            importance=0.8,
            strength=0.4,
            created_at=now - timedelta(days=20),
        )
        engine.practice_answer(item.id, "夏天", now=now)  # failure -> still due
        # with a large gap, the just-practiced item is excluded
        spaced = engine.practice_due(limit=5, now=now, min_gap_hours=48)
        self.assertFalse(any(d["id"] == item.id for d in spaced))
        # with no gap, it can be re-practiced if still due
        massed = engine.practice_due(limit=5, now=now, min_gap_hours=0)
        self.assertTrue(any(d["id"] == item.id for d in massed))

    def test_success_rate_and_adaptive_gap_params(self) -> None:
        engine = MemoryEngine()
        item = engine.remember(
            "阿丽喜欢的颜色是蓝色。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "颜色"],
            importance=0.8,
            strength=0.4,
            created_at=utcnow() - timedelta(days=20),
        )
        item.retrieval_successes = 1
        item.retrieval_failures = 2
        engine.backend.update(item)
        self.assertAlmostEqual(engine._success_rate(item), 1 / 3)
        cards = engine.practice_due(
            limit=5, min_gap_hours=0, adaptive_gap=True
        )
        self.assertTrue(any(c["id"] == item.id for c in cards))
        server = MCPServer(engine=engine)
        result = server._call_tool(
            "practice_due",
            {"limit": 5, "min_gap_hours": 0, "adaptive_gap": True},
        )
        self.assertTrue(isinstance(result, list))

    def test_practice_interleave(self) -> None:
        engine = MemoryEngine()
        for cat, i in (("颜色", 1), ("颜色", 2), ("食物", 3), ("食物", 4)):
            engine.remember(
                f"条目{cat}{i}",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[cat],
                importance=0.8,
                strength=0.4,
                created_at=utcnow() - timedelta(days=20),
            )
        cards = engine.practice_due(
            limit=4, min_gap_hours=0, adaptive_gap=False, interleave=True
        )
        cats = [c["cue"].split(" / ")[0] for c in cards]
        self.assertEqual(len(cats), 4)
        self.assertTrue(all(a != b for a, b in zip(cats, cats[1:])))

    def test_practice_suppress_competitors(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        target = engine.remember(
            "阿丽最喜欢的颜色是琥珀色。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "颜色"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        rival = engine.remember(
            "阿丽以前喜欢的颜色是红色。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "颜色"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        # suppression ON: a successful recall lowers the rival's strength
        rival_strength_before = rival.strength
        ok = engine.practice_answer(target.id, "琥珀色", now=now)
        self.assertTrue(ok["success"])
        self.assertGreaterEqual(ok["suppressed"], 1)
        rival_after = engine.backend.get(rival.id)
        self.assertLess(rival_after.strength, rival_strength_before)
        # suppression OFF: rival strength untouched
        ok2 = engine.practice_answer(
            target.id,
            "琥珀色",
            now=now + timedelta(hours=1),
            suppress_competitors=False,
        )
        self.assertTrue(ok2["success"])
        self.assertEqual(ok2["suppressed"], 0)
        rival_after2 = engine.backend.get(rival.id)
        self.assertAlmostEqual(rival_after2.strength, rival_after.strength)

    def test_mcp_interleave_and_suppress_params(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        target = engine.remember(
            "阿丽最喜欢的食物是饺子。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "食物"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        rival = engine.remember(
            "阿丽以前喜欢的食物是面条。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "食物"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        server = MCPServer(engine=engine)
        cards = server._call_tool(
            "practice_due",
            {"limit": 5, "min_gap_hours": 0, "adaptive_gap": False,
             "interleave": True},
        )
        self.assertTrue(any(c["id"] == target.id for c in cards))
        result = server._call_tool(
            "practice_answer",
            {"memory_id": target.id, "attempt": "饺子",
             "suppress_competitors": False},
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["suppressed"], 0)
        rival_after = engine.backend.get(rival.id)
        self.assertAlmostEqual(rival_after.strength, rival.strength)

    def test_practice_generation_bonus(self) -> None:
        from datetime import timedelta

        def _fresh() -> tuple[MemoryEngine, object]:
            engine = MemoryEngine()
            now = utcnow()
            item = engine.remember(
                "阿丽最喜欢的城市是成都。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=["阿丽", "城市"],
                importance=0.8,
                strength=0.5,
                created_at=now - timedelta(days=20),
            )
            return engine, item

        engine_v, item_v = _fresh()
        res_v = engine_v.practice_answer(
            item_v.id, "阿丽最喜欢的城市是成都。", now=utcnow()
        )
        self.assertTrue(res_v["success"])
        self.assertFalse(res_v["generated"])
        engine_g, item_g = _fresh()
        res_g = engine_g.practice_answer(
            item_g.id,
            "我自己的话：阿丽最喜欢的城市是成都。",
            now=utcnow(),
        )
        self.assertTrue(res_g["success"])
        self.assertTrue(res_g["generated"])
        r_v = engine_v.curve.retrievability(item_v, utcnow())
        r_g = engine_g.curve.retrievability(item_g, utcnow())
        self.assertGreater(r_g, r_v)

    def test_mcp_generation_bonus_param(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        item = engine.remember(
            "阿丽最喜欢的动物是猫。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "动物"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        server = MCPServer(engine=engine)
        result = server._call_tool(
            "practice_answer",
            {
                "memory_id": item.id,
                "attempt": "我自己的话：阿丽最喜欢的动物是猫。",
                "generation_bonus": True,
            },
        )
        self.assertTrue(result["success"])
        self.assertTrue(result["generated"])

    def test_suppression_only_uses_primary_cue(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        target = engine.remember(
            "阿丽最喜欢的城市是成都。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["城市"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        # different primary cue; content shares auto bigrams (阿丽/喜欢/成都)
        # but does NOT contain the target's primary cue "城市"
        other = engine.remember(
            "阿丽喜欢在成都吃火锅。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["火锅"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        other_before = other.strength
        result = engine.practice_answer(
            target.id, "阿丽最喜欢的城市是成都。", now=now
        )
        self.assertTrue(result["success"])
        self.assertEqual(result["suppressed"], 0)
        self.assertAlmostEqual(
            engine.backend.get(other.id).strength, other_before
        )


if __name__ == "__main__":
    unittest.main()
