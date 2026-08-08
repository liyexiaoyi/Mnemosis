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

    def test_mcp_search_tool(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        engine.remember(
            "阿丽喜欢的城市是成都。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "城市"],
            importance=0.8,
            strength=0.5,
            created_at=utcnow() - timedelta(days=20),
        )
        server = MCPServer(engine=engine)
        results = server._call_tool(
            "search", {"query": "阿丽喜欢的城市", "top_k": 3}
        )
        self.assertTrue(results)
        self.assertIn("成都", results[0]["content"])
        self.assertIn("confident", results[0])
        self.assertIn("reasons", results[0])
        self.assertIn("score", results[0])

    def test_mcp_list_conflicts(self) -> None:
        engine = MemoryEngine()
        engine.remember(
            "alpha says 1",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["alpha"],
            confidence=0.8,
        )
        engine.remember(
            "alpha says 2",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["alpha"],
            confidence=0.8,
        )
        server = MCPServer(engine=engine)
        conflicts = server._call_tool("list_conflicts", {})
        self.assertEqual(len(conflicts), 1)
        self.assertEqual(
            {conflicts[0]["a"], conflicts[0]["b"]},
            {"alpha says 1", "alpha says 2"},
        )

    def test_mcp_memory_status(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        engine.remember(
            "due fact",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["due"],
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        engine.remember(
            "fresh event",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["fresh"],
            strength=0.9,
            created_at=now - timedelta(days=1),
        )
        engine.remember(
            "conflict a",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["same"],
            confidence=0.8,
        )
        engine.remember(
            "conflict b",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["same"],
            confidence=0.8,
        )
        server = MCPServer(engine=engine)
        status = server._call_tool("memory_status", {})
        self.assertEqual(status["stats"]["active"], 4)
        self.assertEqual(status["stats"]["semantic"], 3)
        self.assertEqual(status["stats"]["episodic"], 1)
        self.assertGreaterEqual(status["due_now"], 1)
        self.assertEqual(status["conflicts"], 1)

    def test_review_batch(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        items = []
        for i in range(4):
            item = engine.remember(
                f"批量复习{i}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"批量{i}"],
                importance=0.8,
                strength=0.3,
                created_at=now - timedelta(days=20),
            )
            items.append(item)
        answers = [
            {"id": items[0].id, "success": True},
            {"id": items[1].id, "success": True},
            {"id": items[2].id, "success": False},
            {"id": items[3].id, "success": False},
        ]
        report = engine.review_batch(answers, now=now)
        self.assertEqual(report["n"], 4)
        self.assertEqual(report["successes"], 2)
        self.assertEqual(report["failures"], 2)
        by_id = {d["id"]: d for d in report["details"]}
        self.assertGreater(by_id[items[0].id]["review_streak"], 0)
        self.assertEqual(by_id[items[2].id]["review_streak"], 0)
        self.assertIn("next_review_at", by_id[items[0].id])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "review_batch", {"answers": answers}
        )
        self.assertEqual(via_mcp["n"], 4)

    def test_export_import(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        a = engine.remember(
            "导出记忆 a：喜欢红色。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["导出a"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=10),
        )
        engine.remember(
            "导出记忆 b：去过成都。",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["导出b"],
            importance=0.6,
            strength=0.4,
            created_at=now - timedelta(days=5),
        )
        a.retrieval_successes = 3
        a.review_streak = 2
        engine.backend.update(a)
        payload = engine.export_memories()
        self.assertEqual(len(payload["memories"]), 2)
        fresh = MemoryEngine()
        imported = fresh.import_memories(payload)
        self.assertEqual(imported, 2)
        self.assertEqual(len(fresh.store.all_active()), 2)
        restored = next(
            i for i in fresh.store.all_active() if "红色" in i.content
        )
        self.assertEqual(restored.retrieval_successes, 3)
        self.assertEqual(restored.review_streak, 2)
        server = MCPServer(engine=engine)
        via_tool = server._call_tool("export_memories", {})
        self.assertEqual(len(via_tool["memories"]), 2)
        fresh2 = MemoryEngine()
        server2 = MCPServer(engine=fresh2)
        imported2 = server2._call_tool(
            "import_memories", {"payload": via_tool}
        )
        self.assertEqual(imported2, 2)

    def test_practice_session(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        items = []
        for i in range(3):
            item = engine.remember(
                f"会话{i}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"会话{i}"],
                importance=0.8,
                strength=0.3,
                created_at=now - timedelta(days=20),
            )
            items.append(item)
        answers = [
            {"id": item.id, "attempt": "测试"}
            for item in items
        ]
        session = engine.practice_session(answers, limit=3, now=now)
        self.assertEqual(len(session["plan"]), 3)
        self.assertEqual(session["report"]["n"], 3)
        self.assertIsNotNone(session["report"]["difficulty"])
        self.assertTrue(
            all(
                "next_review_at" in d
                for d in session["report"]["details"]
            )
        )
        engine2 = MemoryEngine()
        now2 = utcnow()
        answers2 = []
        for i in range(3):
            item = engine2.remember(
                f"会话b{i}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"会话b{i}"],
                importance=0.8,
                strength=0.3,
                created_at=now2 - timedelta(days=20),
            )
            answers2.append({"id": item.id, "attempt": "测试"})
        server = MCPServer(engine=engine2)
        via_mcp = server._call_tool(
            "practice_session",
            {"limit": 3, "answers": answers2},
        )
        self.assertEqual(len(via_mcp["plan"]), 3)

    def test_sleep_and_plan(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        for i in range(5):
            engine.remember(
                f"弱重要{i}：关键知识。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"弱重要{i}"],
                importance=0.8,
                strength=0.3,
                created_at=now - timedelta(days=60),
            )
        result = engine.sleep_and_plan(days=7, now=now)
        self.assertGreaterEqual(result["weak_replayed"], 1)
        self.assertIsInstance(result["plan"], list)
        self.assertIsInstance(result["forecast"], list)
        self.assertIn("weak_replayed", result["sleep_summary"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "sleep_and_plan", {"days": 7}
        )
        self.assertIn("sleep_summary", via_mcp)

    def test_memory_audit(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        revised = engine.remember(
            "audit old",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["audit-r"],
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.update(revised.id, content="audit new", now=now)
        engine.remember(
            "audit emotional",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["audit-e"],
            affect="negative",
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            "audit event",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["audit-ep"],
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            "audit conflict a",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["audit-c"],
            confidence=0.8,
        )
        engine.remember(
            "audit conflict b",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["audit-c"],
            confidence=0.8,
        )
        trash = engine.remember(
            "audit trash",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["audit-t"],
        )
        engine.forget(trash.id)
        audit = engine.memory_audit(now=now)
        self.assertEqual(audit["active"], 5)
        self.assertEqual(audit["recycled"], 1)
        self.assertGreaterEqual(audit["revised"], 1)
        self.assertGreaterEqual(audit["emotional"], 1)
        self.assertEqual(audit["conflicts"], 1)
        self.assertIn("avg_retrievability", audit)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("memory_audit", {})
        self.assertEqual(via_mcp["active"], 5)

    def test_dedupe_memories(self) -> None:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        for _ in range(3):
            engine.remember(
                "重复事件：同一天去了公园。",
                kind=MemoryKind.EPISODIC,
                source=source,
                cues=["公园", "同一天"],
            )
        engine.remember(
            "唯一事件：去了图书馆。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["图书馆"],
        )
        before = len(engine.store.all_active())
        merged = engine.dedupe_memories()
        after = len(engine.store.all_active())
        self.assertEqual(merged, 2)
        self.assertEqual(after, before - 2)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("dedupe_memories", {})
        self.assertIsInstance(via_mcp, int)

    def test_resolve_conflicts(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "强证据方：版本 5。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["冲突a"],
            confidence=0.8,
            evidence_count=5,
            auto_cues=False,
        )
        engine.remember(
            "弱证据方：版本 1。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["冲突a"],
            confidence=0.8,
            evidence_count=1,
            auto_cues=False,
        )
        engine.remember(
            "平衡甲：立场 A。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["冲突b"],
            confidence=0.8,
            evidence_count=1,
            auto_cues=False,
        )
        engine.remember(
            "平衡乙：立场 B。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["冲突b"],
            confidence=0.8,
            evidence_count=1,
            auto_cues=False,
        )
        result = engine.resolve_conflicts()
        self.assertGreaterEqual(result["accommodated"], 1)
        self.assertGreaterEqual(result["rem_resolved"], 1)
        self.assertGreaterEqual(result["remaining"], 1)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("resolve_conflicts", {})
        self.assertIn("remaining", via_mcp)

    def test_review_load(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        for i in range(2):
            item = engine.remember(
                f"逾期{i}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"逾期{i}"],
                strength=0.3,
                created_at=now - timedelta(days=20),
            )
            item.last_review_at = now - timedelta(days=3)
            engine.backend.update(item)
        for i in range(3):
            engine.remember(
                f"到期{i}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"到期{i}"],
                strength=0.3,
                created_at=now - timedelta(days=20),
            )
        load = engine.review_load(days=7, now=now)
        self.assertEqual(load["overdue"], 2)
        self.assertGreaterEqual(load["due_now"], 5)
        self.assertGreaterEqual(load["weak"], 5)
        self.assertGreaterEqual(load["load_index"], 5)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("review_load", {"days": 7})
        self.assertIn("load_index", via_mcp)

    def test_tag_memories(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        items = []
        for i in range(2):
            item = engine.remember(
                f"标签{i}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["base"],
                auto_cues=False,
            )
            items.append(item)
        result = engine.tag_memories(
            [item.id for item in items], ["工作", "项目"], action="add"
        )
        self.assertEqual(result["updated"], 2)
        self.assertEqual(result["added"], 4)
        first = engine.backend.get(items[0].id)
        self.assertIn("工作", first.cues)
        self.assertIn("项目", first.cues)
        removed = engine.tag_memories(
            [item.id for item in items], ["项目"], action="remove"
        )
        self.assertEqual(removed["removed"], 2)
        self.assertNotIn("项目", engine.backend.get(items[0].id).cues)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "tag_memories",
            {
                "memory_ids": [item.id for item in items],
                "tags": ["临时"],
                "action": "add",
            },
        )
        self.assertEqual(via_mcp["updated"], 2)

    def test_recall_log(self) -> None:
        engine = MemoryEngine()
        item = engine.remember(
            "日志记忆：内容甲。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["日志a"],
        )
        engine.recall("日志a", top_k=3)
        log = engine.get_recall_log(limit=10)
        self.assertGreaterEqual(len(log), 1)
        self.assertEqual(log[-1]["query"], "日志a")
        self.assertEqual(log[-1]["top_id"], item.id)
        self.assertIn("confident", log[-1])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("recall_log", {"limit": 5})
        self.assertGreaterEqual(len(via_mcp), 1)

    def test_cleanup_preview(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        for i in range(2):
            engine.remember(
                f"可清理{i}：旧琐碎事件。",
                kind=MemoryKind.EPISODIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"可清理{i}"],
                importance=0.1,
                created_at=now - timedelta(days=40),
            )
        engine.remember(
            "重要旧事件。",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["重要旧"],
            importance=0.8,
            created_at=now - timedelta(days=40),
        )
        accessed = engine.remember(
            "被访问过的旧事件。",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["访问旧"],
            importance=0.1,
            created_at=now - timedelta(days=40),
        )
        accessed.access_count = 3
        engine.backend.update(accessed)
        before = len(engine.store.all_active())
        preview = engine.cleanup_preview(now=now)
        self.assertEqual(len(preview), 2)
        self.assertEqual(len(engine.store.all_active()), before)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("cleanup_preview", {"limit": 10})
        self.assertEqual(len(via_mcp), 2)

    def test_similarity_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        a = engine.remember(
            "阿丽喜欢红色。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["相似a"],
        )
        b = engine.remember(
            "阿丽喜欢红色！",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["相似b"],
        )
        engine.remember(
            "小明去了北京。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["不同c"],
        )
        report = engine.similarity_report(threshold=0.6)
        self.assertEqual(len(report), 1)
        self.assertEqual({report[0]["a_id"], report[0]["b_id"]}, {a.id, b.id})
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "similarity_report", {"threshold": 0.6}
        )
        self.assertEqual(len(via_mcp), 1)

    def test_association_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        hub = engine.remember(
            "zzz hub one.", kind=MemoryKind.SEMANTIC, source=user
        )
        nodes = [
            engine.remember(
                f"qqq nod {i}.", kind=MemoryKind.SEMANTIC, source=user
            )
            for i in range(5)
        ]
        isolated = [
            engine.remember(
                f"aaa lon {i}.", kind=MemoryKind.SEMANTIC, source=user
            )
            for i in range(6)
        ]
        for node in nodes:
            engine.backend.add_link(hub.id, node.id)
        engine.backend.add_link(nodes[0].id, nodes[1].id)
        engine.backend.add_link(nodes[2].id, nodes[3].id)
        report = engine.association_report(limit=3)
        self.assertEqual(report["memory_count"], 12)
        self.assertEqual(report["directed_links"], 7)
        self.assertEqual(report["unique_pairs"], 7)
        self.assertEqual(report["connected_count"], 6)
        self.assertEqual(report["isolated_count"], 6)
        self.assertEqual(report["avg_links"], round(14 / 12, 3))
        self.assertEqual(report["top_connected"][0]["id"], hub.id)
        self.assertEqual(report["top_connected"][0]["link_count"], 5)
        self.assertNotIn(isolated[0].id, {t["id"] for t in report["top_connected"]})
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("association_report", {"limit": 2})
        self.assertEqual(via_mcp["directed_links"], 7)
        self.assertEqual(len(via_mcp["top_connected"]), 2)

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

    def test_practice_report_review_suggestions(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        good = engine.remember(
            "阿丽喜欢的城市是成都。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "城市"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        bad = engine.remember(
            "阿丽喜欢的食物是饺子。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["阿丽", "食物"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
        report = engine.practice_report(
            [
                {"id": good.id, "attempt": "阿丽喜欢的城市是成都。"},
                {"id": bad.id, "attempt": "完全错误"},
            ],
            now=now,
        )
        by_id = {d["id"]: d for d in report["details"]}
        self.assertIn("next_review_at", by_id[good.id])
        self.assertAlmostEqual(by_id[good.id]["retry_hours"], 24.0)
        self.assertAlmostEqual(by_id[bad.id]["retry_hours"], 12.0)

    def test_practice_report_difficulty(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        items = []
        for strength in (0.3, 0.6, 0.9):
            item = engine.remember(
                f"难度记忆{strength}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"难度{strength}"],
                importance=0.8,
                strength=strength,
                created_at=now - timedelta(days=20),
            )
            items.append(item)
        report = engine.practice_report(
            [{"id": item.id, "attempt": "随便答"} for item in items],
            now=now,
        )
        diff = report["difficulty"]
        self.assertEqual(diff["n"], 3)
        self.assertAlmostEqual(
            diff["mean_difficulty"],
            1.0 - diff["mean_retrievability"],
            places=3,
        )
        self.assertGreaterEqual(diff["min_retrievability"], 0.0)
        self.assertLessEqual(diff["max_retrievability"], 1.0)
        self.assertLess(diff["min_retrievability"], diff["max_retrievability"])

    def test_practice_plan(self) -> None:
        from datetime import datetime, timedelta

        engine = MemoryEngine()
        now = utcnow()
        items = []
        for i in range(3):
            item = engine.remember(
                f"计划记忆{i}：条目{i}。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"计划{i}"],
                importance=0.8,
                strength=0.3,
                created_at=now - timedelta(days=20),
            )
            items.append(item)
        items[0].review_streak = 0
        items[1].review_streak = 1
        items[2].review_streak = 2
        for item in items:
            engine.backend.update(item)
        plan = engine.practice_plan(limit=5, now=now)
        by_id = {entry["id"]: entry for entry in plan}
        for item in items:
            self.assertIn(item.id, by_id)
        self.assertIn("next_review_at", by_id[items[0].id])
        self.assertIn("success_rate", by_id[items[0].id])

        def _hours(entry) -> float:
            return (
                datetime.fromisoformat(entry["next_review_at"]) - now
            ).total_seconds() / 3600.0

        self.assertAlmostEqual(_hours(by_id[items[0].id]), 12.0)
        self.assertAlmostEqual(_hours(by_id[items[1].id]), 24.0)
        self.assertAlmostEqual(_hours(by_id[items[2].id]), 48.0)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("practice_plan", {"limit": 5})
        self.assertEqual(len(via_mcp), 3)

    def test_practice_forecast(self) -> None:
        from datetime import datetime, timedelta

        engine = MemoryEngine()
        now = utcnow()
        items = {}
        for streak in (0, 1, 2, 8, 9):
            item = engine.remember(
                f"预报记忆{streak}：条目{streak}。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"预报{streak}"],
                importance=0.8,
                strength=0.3,
                created_at=now - timedelta(days=20),
            )
            item.review_streak = streak
            engine.backend.update(item)
            items[streak] = item.id
        forecast = engine.practice_forecast(days=7, now=now)
        ids = {entry["id"] for entry in forecast}
        self.assertIn(items[0], ids)
        self.assertIn(items[1], ids)
        self.assertIn(items[2], ids)
        self.assertNotIn(items[8], ids)
        self.assertNotIn(items[9], ids)
        due_times = [
            datetime.fromisoformat(entry["due_at"]) for entry in forecast
        ]
        self.assertEqual(due_times, sorted(due_times))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "practice_forecast", {"days": 7}
        )
        self.assertEqual(len(via_mcp), len(forecast))

    def test_overdue_flags(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        overdue = engine.remember(
            "逾期记忆：很久没复习。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["逾期"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        overdue.last_review_at = now - timedelta(days=3)
        engine.backend.update(overdue)
        future = engine.remember(
            "未来记忆：刚复习过。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["未来"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        future.last_review_at = now
        engine.backend.update(future)
        plan = engine.practice_plan(limit=5, now=now)
        by_id = {entry["id"]: entry for entry in plan}
        self.assertTrue(by_id[overdue.id]["overdue"])
        self.assertFalse(by_id[future.id]["overdue"])
        forecast = engine.practice_forecast(days=7, now=now)
        f_by_id = {entry["id"]: entry for entry in forecast}
        self.assertTrue(f_by_id[overdue.id]["overdue"])
        self.assertLess(
            forecast.index(f_by_id[overdue.id]),
            forecast.index(f_by_id[future.id]),
        )

    def test_review_score_priority(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        important = engine.remember(
            "重要但不急：高重要度记忆。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["重要"],
            importance=0.9,
            strength=0.5,
            created_at=now - timedelta(days=1),
        )
        fading = engine.remember(
            "没那么重要但快忘：中重要度弱记忆。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["快忘"],
            importance=0.6,
            strength=0.5,
            created_at=now - timedelta(days=40),
        )
        score = engine.practice_due(
            limit=2,
            min_gap_hours=0,
            adaptive_gap=False,
            desirable_difficulty=False,
            review_score_priority=True,
        )
        self.assertEqual(score[0]["id"], fading.id)
        plain = engine.practice_due(
            limit=2,
            min_gap_hours=0,
            adaptive_gap=False,
            desirable_difficulty=False,
            review_score_priority=False,
        )
        self.assertEqual(plain[0]["id"], important.id)

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

    def test_practice_kind_preference(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        for i in range(2):
            engine.remember(
                f"事实记忆{i}：某条稳定事实{i}。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"事实{i}"],
                importance=0.8,
                strength=0.4,
                created_at=now - timedelta(days=20),
            )
            engine.remember(
                f"事件记忆{i}：某次发生的事{i}。",
                kind=MemoryKind.EPISODIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"事件{i}"],
                importance=0.8,
                strength=0.4,
                created_at=now - timedelta(days=20),
            )
        cards = engine.practice_due(
            limit=4,
            min_gap_hours=0,
            adaptive_gap=False,
            kind=MemoryKind.SEMANTIC,
        )
        self.assertEqual(len(cards), 4)
        self.assertTrue(cards[0]["cue"].startswith("事实"))
        self.assertTrue(cards[1]["cue"].startswith("事实"))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "practice_due",
            {
                "limit": 4,
                "min_gap_hours": 0,
                "adaptive_gap": False,
                "kind": "semantic",
            },
        )
        self.assertTrue(via_mcp[0]["cue"].startswith("事实"))

    def test_practice_vary_cues(self) -> None:
        from datetime import timedelta

        def _build() -> tuple[MemoryEngine, object]:
            engine = MemoryEngine()
            now = utcnow()
            item = engine.remember(
                "阿丽最喜欢的颜色是琥珀色。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=["阿丽", "颜色", "琥珀"],
                importance=0.8,
                strength=0.4,
                created_at=now - timedelta(days=20),
            )
            item.retrieval_successes = 2
            engine.backend.update(item)
            return engine, item

        engine_v, _ = _build()
        varied = engine_v.practice_due(
            limit=5, min_gap_hours=0, adaptive_gap=False, vary_cues=True
        )
        self.assertEqual(varied[0]["cue"], "琥珀 / 喜欢")
        engine_f, _ = _build()
        fixed = engine_f.practice_due(
            limit=5, min_gap_hours=0, adaptive_gap=False, vary_cues=False
        )
        self.assertEqual(fixed[0]["cue"], "阿丽 / 颜色")
        engine_1, item_1 = _build()
        item_1.retrieval_successes = 1
        engine_1.backend.update(item_1)
        varied1 = engine_1.practice_due(
            limit=5, min_gap_hours=0, adaptive_gap=False, vary_cues=True
        )
        self.assertEqual(varied1[0]["cue"], "颜色 / 琥珀")
        server = MCPServer(engine=engine_f)
        via_mcp = server._call_tool(
            "practice_due",
            {
                "limit": 5,
                "min_gap_hours": 0,
                "adaptive_gap": False,
                "vary_cues": False,
            },
        )
        self.assertIn(" / ", via_mcp[0]["cue"])

    def test_practice_arousal_priority(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        for i in range(2):
            engine.remember(
                f"中性记忆{i}：普通记录{i}。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"中性{i}"],
                importance=0.8,
                strength=0.4,
                created_at=now - timedelta(days=20),
            )
            engine.remember(
                f"情绪记忆{i}：那次很紧张。",
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(origin=SourceType.USER),
                cues=[f"情绪{i}"],
                affect="negative",
                importance=0.8,
                strength=0.4,
                created_at=now - timedelta(days=20),
            )
        cards = engine.practice_due(
            limit=4,
            min_gap_hours=0,
            adaptive_gap=False,
            arousal_priority=True,
        )
        first_two = [engine.backend.get(c["id"]) for c in cards[:2]]
        self.assertTrue(
            all(item.affect == "negative" for item in first_two)
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "practice_due",
            {
                "limit": 4,
                "min_gap_hours": 0,
                "adaptive_gap": False,
                "arousal_priority": True,
            },
        )
        self.assertEqual(len(via_mcp), 4)

    def test_practice_fresh_priority(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        fresh = engine.remember(
            "刚发生的事：今天的新记录。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["新鲜"],
            importance=0.5,
            strength=0.4,
            created_at=now - timedelta(hours=2),
        )
        old = engine.remember(
            "很久以前的事：旧记录。",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["陈旧"],
            importance=0.5,
            strength=0.4,
            created_at=now - timedelta(days=20),
        )
        cards = engine.practice_due(
            limit=2,
            min_gap_hours=0,
            adaptive_gap=False,
            desirable_difficulty=False,
            fresh_priority=True,
        )
        self.assertEqual(cards[0]["id"], fresh.id)
        cards_off = engine.practice_due(
            limit=2,
            min_gap_hours=0,
            adaptive_gap=False,
            desirable_difficulty=False,
            fresh_priority=False,
        )
        self.assertEqual(cards_off[0]["id"], old.id)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "practice_due",
            {
                "limit": 2,
                "min_gap_hours": 0,
                "adaptive_gap": False,
                "desirable_difficulty": False,
                "fresh_priority": True,
            },
        )
        self.assertEqual(via_mcp[0]["id"], fresh.id)

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
