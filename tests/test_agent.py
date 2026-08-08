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

    def test_search_batch(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        a = engine.remember(
            "alpha batch memory.", kind=MemoryKind.SEMANTIC, source=user,
            cues=["alpha-key"],
        )
        b = engine.remember(
            "beta batch memory.", kind=MemoryKind.SEMANTIC, source=user,
            cues=["beta-key"],
        )
        groups = engine.search_batch(
            ["alpha-key", "beta-key", "missing-key"], top_k=2
        )
        self.assertEqual(len(groups), 3)
        self.assertEqual([g["query"] for g in groups], [
            "alpha-key", "beta-key", "missing-key"
        ])
        self.assertEqual([g["count"] for g in groups], [2, 2, 2])
        self.assertEqual(groups[0]["results"][0]["id"], a.id)
        self.assertEqual(groups[1]["results"][0]["id"], b.id)
        self.assertLess(
            groups[2]["results"][0]["score"],
            groups[0]["results"][0]["score"],
        )
        self.assertIn("score", groups[0]["results"][0])
        self.assertIn("confident", groups[0]["results"][0])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "search_batch", {"queries": ["alpha-key", "missing-key"]}
        )
        self.assertEqual(len(via_mcp), 2)
        self.assertEqual(via_mcp[0]["count"], 2)
        self.assertEqual(via_mcp[1]["count"], 2)

    def test_intent_register(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        i1 = engine.remember_intent(
            "send report", due_at=now - timedelta(hours=1)
        )
        i2 = engine.remember_intent(
            "pay bill", due_at=now - timedelta(hours=2)
        )
        i3 = engine.remember_intent(
            "book meeting", due_at=now + timedelta(days=1),
            context_cue="office",
        )
        due = engine.intent_due(now=now)
        self.assertEqual([r["id"] for r in due], [i2["id"], i1["id"]])
        report = engine.intent_report(now=now)
        self.assertEqual(report["active"], 3)
        self.assertEqual(report["overdue"], 2)
        self.assertEqual(report["next_upcoming"]["id"], i3["id"])
        self.assertIsNone(engine.complete_intent("missing-id"))
        completed = engine.complete_intent(i1["id"], now=now)
        self.assertEqual(completed["status"], "completed")
        self.assertEqual(engine.intent_due(now=now)[0]["id"], i2["id"])
        self.assertIsNone(engine.complete_intent(i1["id"]))
        cancelled = engine.cancel_intent(i3["id"])
        self.assertEqual(cancelled["status"], "cancelled")
        report = engine.intent_report(now=now)
        self.assertEqual(report["active"], 1)
        self.assertEqual(report["completed"], 1)
        self.assertEqual(report["cancelled"], 1)
        payload = engine.export_memories()
        fresh = MemoryEngine()
        fresh.import_memories(payload)
        self.assertEqual(fresh.intent_report(now=now), report)
        self.assertEqual(
            fresh.intent_due(now=now)[0]["id"], i2["id"]
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "intent_remember",
            {
                "content": "mcp intent",
                "due_at": (now + timedelta(minutes=5)).isoformat(),
            },
        )
        self.assertEqual(via_mcp["status"], "active")
        self.assertGreaterEqual(
            len(server._call_tool("intent_due", {"limit": 10})), 0
        )
        self.assertIn(
            "active", server._call_tool("intent_report", {})
        )

    def test_retrieval_assist(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "用户喜欢颜色偏蓝的配色",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["颜色偏好", "蓝色主题"],
        )
        engine.remember(
            "计划去北京旅行",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["旅行计划"],
        )
        assist = engine.retrieval_assist("色彩")
        self.assertIn(
            "颜色偏好", [s["cue"] for s in assist["suggestions"]]
        )
        self.assertIn("颜色", assist["new_synonyms"])
        self.assertIn(
            "颜色", assist["top_recall"][0]["preview"]
        )
        assist2 = engine.retrieval_assist("旅游")
        self.assertIn(
            "旅行计划", [s["cue"] for s in assist2["suggestions"]]
        )
        self.assertIn("旅行", assist2["new_synonyms"])
        self.assertIn(
            "旅行", assist2["top_recall"][0]["preview"]
        )
        self.assertLessEqual(len(assist["suggestions"]), 8)
        self.assertIn("expanded_terms", assist)
        self.assertIn("source", assist["suggestions"][0])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "retrieval_assist", {"query": "色彩", "limit": 5}
        )
        self.assertIn(
            "颜色偏好", [s["cue"] for s in via_mcp["suggestions"]]
        )

    def test_schema_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for i in range(3):
            engine.remember(
                f"work item {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["工作"],
                importance=0.8,
                auto_cues=False,
            )
        engine.remember(
            "life fact", kind=MemoryKind.SEMANTIC, source=user,
            cues=["生活"], auto_cues=False,
        )
        engine.remember(
            "life event", kind=MemoryKind.EPISODIC, source=user,
            cues=["生活"], auto_cues=False,
        )
        engine.remember(
            "zzz none", kind=MemoryKind.SEMANTIC, source=user,
            auto_cues=False,
        )
        report = engine.schema_report(limit=10)
        self.assertEqual(report["total_memories"], 6)
        self.assertEqual(report["group_count"], 3)
        top = report["top_groups"]
        self.assertEqual(top[0]["topic"], "工作")
        self.assertEqual(top[0]["memory_count"], 3)
        life = next(g for g in top if g["topic"] == "生活")
        self.assertEqual(life["memory_count"], 2)
        self.assertEqual(life["kinds"], {"semantic": 1, "episodic": 1})
        untagged = next(g for g in top if g["topic"] == "（无标签）")
        self.assertEqual(untagged["memory_count"], 1)
        self.assertTrue(all(g["samples"] for g in top))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("schema_report", {"limit": 5})
        self.assertEqual(via_mcp["group_count"], 3)
        self.assertEqual(via_mcp["top_groups"][0]["topic"], "工作")

    def test_suppress_memories(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        a = engine.remember(
            "aaa suppress me", kind=MemoryKind.SEMANTIC, source=user,
            cues=["sup-a"], auto_cues=False,
        )
        b = engine.remember(
            "bbb keep me", kind=MemoryKind.SEMANTIC, source=user,
            cues=["sup-b"], auto_cues=False,
        )
        c = engine.remember(
            "ccc keep me too", kind=MemoryKind.SEMANTIC, source=user,
            cues=["sup-c"], auto_cues=False,
        )
        result = engine.suppress_memories([a.id])
        self.assertEqual(result["suppressed"], 1)
        self.assertEqual(engine.suppress_memories([a.id])["suppressed"], 0)
        recalled_a = engine.recall("sup-a", top_k=3)
        self.assertNotIn(a.id, {r.item.id for r in recalled_a})
        self.assertIn(b.id, {r.item.id for r in engine.recall("sup-b")})
        self.assertEqual(
            len(engine.store.all_active()), 3
        )
        report = engine.suppressed_report()
        self.assertEqual(report["count"], 1)
        self.assertEqual(report["memories"][0]["id"], a.id)
        self.assertEqual(
            engine.unsuppress_memories([a.id])["unsuppressed"], 1
        )
        self.assertIn(
            a.id, {r.item.id for r in engine.recall("sup-a", top_k=3)}
        )
        engine.suppress_memories([b.id])
        payload = engine.export_memories()
        fresh = MemoryEngine()
        fresh.import_memories(payload)
        self.assertEqual(fresh.suppressed_report()["count"], 1)
        self.assertNotIn(
            b.id, {r.item.id for r in fresh.recall("sup-b", top_k=3)}
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "suppressed_report", {}
        )
        self.assertEqual(via_mcp["count"], 1)
        self.assertEqual(
            server._call_tool(
                "unsuppress_memories", {"memory_ids": [b.id]}
            )["unsuppressed"],
            1,
        )

    def test_timeline_report(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
        for day in range(3):
            for slot in range(2):
                engine.remember(
                    f"event d{day} s{slot}",
                    kind=MemoryKind.EPISODIC,
                    source=user,
                    cues=[f"tl-{day}-{slot}"],
                    created_at=(
                        now - timedelta(days=2 - day) + timedelta(hours=slot)
                    ),
                    auto_cues=False,
                )
        engine.remember(
            "semantic fact", kind=MemoryKind.SEMANTIC, source=user,
            auto_cues=False,
        )
        report = engine.timeline_report()
        self.assertEqual(report["total"], 6)
        self.assertEqual(len(report["days"]), 3)
        self.assertTrue(all(d["count"] == 2 for d in report["days"]))
        dates = [d["date"] for d in report["days"]]
        self.assertEqual(dates, sorted(dates))
        window = engine.timeline_report(
            start=now - timedelta(days=1),
            end=now + timedelta(days=1),
        )
        self.assertEqual(window["total"], 4)
        self.assertEqual(len(window["days"]), 2)
        self.assertEqual(
            report["days"][0]["items"][0]["kind"], "episodic"
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("timeline_report", {"limit": 50})
        self.assertEqual(via_mcp["total"], 6)

    def test_recognition_check(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        m1 = engine.remember(
            "alpha unique zebra", kind=MemoryKind.SEMANTIC, source=user,
            cues=["alpha-key"], auto_cues=False,
        )
        engine.remember(
            "beta term", kind=MemoryKind.SEMANTIC, source=user,
            cues=["beta-key"], auto_cues=False,
        )
        m3 = engine.remember(
            "gamma unrelated", kind=MemoryKind.SEMANTIC, source=user,
            cues=["gamma-key"], auto_cues=False,
        )
        rec = engine.recognition_check("alpha-key", m1.id)
        self.assertEqual(rec["verdict"], "recollection")
        self.assertGreaterEqual(rec["overlap"], 0.6)
        fam = engine.recognition_check("alpha extra", m1.id)
        self.assertEqual(fam["verdict"], "familiarity")
        self.assertLess(fam["overlap"], 0.6)
        miss = engine.recognition_check("alpha-key", m3.id)
        self.assertEqual(miss["verdict"], "unmatched")
        self.assertEqual(miss["overlap"], 0.0)
        missing = engine.recognition_check("alpha-key", "nope")
        self.assertEqual(missing["verdict"], "missing")
        self.assertIn("score", rec)
        self.assertIn("confidence", rec)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "recognition_check", {"query": "alpha-key", "memory_id": m1.id}
        )
        self.assertEqual(via_mcp["verdict"], "recollection")

    def test_interference_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for i in range(5):
            engine.remember(
                f"meeting item alpha {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["会议"],
                auto_cues=False,
            )
        for i in range(3):
            engine.remember(
                f"project item beta {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["项目"],
                auto_cues=False,
            )
        engine.remember(
            "solo gamma", kind=MemoryKind.SEMANTIC, source=user,
            cues=["唯一"], auto_cues=False,
        )
        engine.remember(
            "solo delta", kind=MemoryKind.SEMANTIC, source=user,
            cues=["独有"], auto_cues=False,
        )
        report = engine.interference_report(shared_cue_min=3)
        by_cue = {c["cue"]: c for c in report["crowded_clusters"]}
        self.assertIn("会议", by_cue)
        self.assertIn("项目", by_cue)
        self.assertEqual(by_cue["会议"]["memory_count"], 5)
        self.assertEqual(by_cue["项目"]["memory_count"], 3)
        self.assertEqual(
            report["crowded_clusters"][0]["cue"], "会议"
        )
        self.assertTrue(report["suggestion"])
        self.assertTrue(all(c["members"] for c in report["crowded_clusters"]))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "interference_report", {"shared_cue_min": 3}
        )
        self.assertEqual(
            {c["cue"] for c in via_mcp["crowded_clusters"]},
            {"会议", "项目"},
        )

    def test_life_story(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        themes = ["工作", "生活", "旅行"]
        for offset in (75, 40, 8):
            for slot, theme in enumerate(themes):
                engine.remember(
                    f"story {theme} {slot}",
                    kind=MemoryKind.EPISODIC,
                    source=user,
                    cues=[theme],
                    importance=0.5 + 0.1 * slot,
                    created_at=now - timedelta(days=offset, hours=slot),
                    auto_cues=False,
                )
        story = engine.life_story(period_days=30)
        self.assertEqual(story["total_events"], 9)
        self.assertEqual(len(story["periods"]), 3)
        self.assertTrue(all(p["event_count"] == 3 for p in story["periods"]))
        self.assertTrue(
            all(
                {t["cue"] for t in p["top_themes"]} == set(themes)
                and all(t["count"] == 1 for t in p["top_themes"])
                for p in story["periods"]
            )
        )
        self.assertTrue(all(p["highlights"] for p in story["periods"]))
        self.assertGreater(
            story["periods"][0]["highlights"][0]["importance"],
            story["periods"][0]["highlights"][-1]["importance"],
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("life_story", {"period_days": 30})
        self.assertEqual(via_mcp["total_events"], 9)
        self.assertEqual(len(via_mcp["periods"]), 3)

    def test_intent_conflicts(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        i1 = engine.remember_intent("call a", due_at=now + timedelta(minutes=10))
        i2 = engine.remember_intent("call b", due_at=now + timedelta(minutes=20))
        i3 = engine.remember_intent("later", due_at=now + timedelta(hours=2))
        i4 = engine.remember_intent(
            "office a", due_at=now + timedelta(days=1), context_cue="office"
        )
        i5 = engine.remember_intent(
            "office b", due_at=now + timedelta(days=2), context_cue="office"
        )
        result = engine.intent_conflicts(time_window_minutes=60)
        self.assertEqual(result["total"], 2)
        time_hit = next(
            c for c in result["conflicts"] if c["type"] == "time"
        )
        self.assertEqual(
            {time_hit["intent_a"], time_hit["intent_b"]}, {i1["id"], i2["id"]}
        )
        self.assertEqual(time_hit["gap_minutes"], 10.0)
        context_hit = next(
            c for c in result["conflicts"] if c["type"] == "context"
        )
        self.assertEqual(context_hit["cue"], "office")
        self.assertNotIn(
            i3["id"],
            {c["intent_a"] for c in result["conflicts"]}
            | {c["intent_b"] for c in result["conflicts"]},
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "intent_conflicts", {"time_window_minutes": 60}
        )
        self.assertEqual(via_mcp["total"], 2)

    def test_memory_health(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        hub = engine.remember(
            "zzz hub one.", kind=MemoryKind.SEMANTIC, source=user
        )
        nodes = [
            engine.remember(
                f"qqq nod {i}.", kind=MemoryKind.SEMANTIC, source=user
            )
            for i in range(5)
        ]
        for node in nodes:
            engine.backend.add_link(hub.id, node.id)
        for i in range(2):
            engine.remember(
                f"aaa lon {i}.", kind=MemoryKind.SEMANTIC, source=user
            )
        engine.remember(
            "conflict alpha", kind=MemoryKind.SEMANTIC, source=user,
            cues=["conflict-key"], confidence=0.8, auto_cues=False,
        )
        engine.remember(
            "conflict beta", kind=MemoryKind.SEMANTIC, source=user,
            cues=["conflict-key"], confidence=0.8, auto_cues=False,
        )
        for i in range(3):
            engine.remember(
                f"crowd {i} item", kind=MemoryKind.SEMANTIC, source=user,
                cues=["会议"], auto_cues=False,
            )
        engine.remember_intent(
            "overdue task", due_at=now - timedelta(hours=1)
        )
        engine.remember_intent(
            "clash a", due_at=now + timedelta(minutes=10)
        )
        engine.remember_intent(
            "clash b", due_at=now + timedelta(minutes=20)
        )
        health = engine.memory_health()
        self.assertEqual(health["memory_count"], 13)
        self.assertEqual(health["linked_ratio"], round(11 / 13, 3))
        self.assertGreaterEqual(health["crowded_clusters"], 1)
        self.assertGreaterEqual(health["conflicts"], 1)
        self.assertGreaterEqual(health["overdue_intents"], 1)
        self.assertGreaterEqual(health["intent_clashes"], 1)
        self.assertLess(health["score"], 100)
        self.assertGreaterEqual(health["score"], 0)
        self.assertGreater(sum(health["penalties"].values()), 0)
        self.assertEqual(
            health["score"],
            max(0, 100 - sum(health["penalties"].values())),
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("memory_health", {})
        self.assertEqual(via_mcp["memory_count"], 13)
        self.assertIn("penalties", via_mcp)

    def test_kg_export(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        hub = engine.remember(
            "zzz hub alpha.", kind=MemoryKind.SEMANTIC, source=user
        )
        nodes = [
            engine.remember(
                f"qqq nod {letter}.", kind=MemoryKind.SEMANTIC, source=user
            )
            for letter in ("x", "y", "z", "u")
        ]
        for node in nodes:
            engine.backend.add_link(hub.id, node.id)
        engine.remember("aaa lon m.", kind=MemoryKind.SEMANTIC, source=user)
        engine.remember("aaa lon n.", kind=MemoryKind.SEMANTIC, source=user)
        graph = engine.kg_export()
        self.assertEqual(graph["node_count"], 7)
        self.assertEqual(graph["edge_count"], 4)
        self.assertIn(hub.id, {n["id"] for n in graph["nodes"]})
        self.assertEqual(graph["nodes"][0]["kind"], "semantic")
        pairs = {
            frozenset((e["source"], e["target"])) for e in graph["edges"]
        }
        self.assertEqual(len(pairs), 4)
        self.assertTrue(
            all(
                {"source", "target", "weight"} <= set(e)
                for e in graph["edges"]
            )
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("kg_export", {})
        self.assertEqual(via_mcp["node_count"], 7)
        self.assertEqual(via_mcp["edge_count"], 4)

    def test_learner_profile(self) -> None:
        user = SourceRecord(origin=SourceType.USER)

        def _store(successes: int, failures: int) -> MemoryEngine:
            engine = MemoryEngine()
            for i in range(4):
                item = engine.remember(
                    f"learner {i}",
                    kind=MemoryKind.SEMANTIC,
                    source=user,
                    cues=[f"lp-{i}"],
                    auto_cues=False,
                )
                item.retrieval_successes = successes
                item.retrieval_failures = failures
                engine.backend.update(item)
            return engine

        fast = _store(3, 0).learner_profile()
        self.assertEqual(fast["total_memories"], 4)
        self.assertEqual(fast["total_reviews"], 12)
        self.assertEqual(fast["success_rate"], 1.0)
        self.assertEqual(fast["profile"], "fast")
        self.assertEqual(fast["suggested_interval_scale"], 1.2)
        slow = _store(1, 3).learner_profile()
        self.assertEqual(slow["success_rate"], 0.25)
        self.assertEqual(slow["profile"], "struggling")
        self.assertEqual(slow["suggested_interval_scale"], 0.8)
        empty = MemoryEngine().learner_profile()
        self.assertEqual(empty["profile"], "unknown")
        server = MCPServer(engine=_store(2, 1))
        via_mcp = server._call_tool("learner_profile", {})
        self.assertIn("profile", via_mcp)
        self.assertIn("suggested_interval_scale", via_mcp)

    def test_context_pack(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        a = engine.remember(
            "packed memory alpha content here",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["pack-a1", "pack-a2"],
            auto_cues=False,
        )
        engine.remember(
            "packed memory beta content here too",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["pack-b"],
            auto_cues=False,
        )
        pack = engine.context_pack(
            ["pack-a1", "pack-a2", "pack-b"],
            top_k=2,
            max_chars=100,
        )
        self.assertEqual(pack["query_count"], 3)
        self.assertEqual(pack["unique_found"], 2)
        ids = [p["id"] for p in pack["packed"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertLessEqual(pack["packed_chars"], 100)
        self.assertTrue(
            all(
                pack["packed"][i]["score"]
                >= pack["packed"][i + 1]["score"]
                for i in range(len(pack["packed"]) - 1)
            )
        )
        self.assertEqual(
            pack["packed"][0]["id"], a.id
        )
        self.assertIn("total_found", pack)
        self.assertIn("truncated_count", pack)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "context_pack",
            {"queries": ["pack-a1", "pack-b"], "max_chars": 100},
        )
        self.assertEqual(via_mcp["unique_found"], 2)

    def test_encoding_quality(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        good = engine.remember(
            "今天在办公室完成预算报告，讨论了三个方案",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["预算", "方案"],
            context="办公室",
            affect="positive",
            importance=0.8,
            strength=0.7,
            auto_cues=False,
        )
        weak = engine.remember(
            "zzz", kind=MemoryKind.EPISODIC, source=user, auto_cues=False
        )
        mid = engine.remember(
            "mid quality memory", kind=MemoryKind.EPISODIC, source=user,
            cues=["中间"], affect="positive", auto_cues=False,
        )
        good_q = engine.encoding_quality(good.id)
        self.assertGreaterEqual(good_q["score"], 80)
        self.assertEqual(good_q["verdict"], "well_encoded")
        weak_q = engine.encoding_quality(weak.id)
        self.assertLess(weak_q["score"], 60)
        self.assertEqual(weak_q["verdict"], "weak")
        self.assertTrue(weak_q["suggestions"])
        mid_q = engine.encoding_quality(mid.id)
        self.assertGreaterEqual(mid_q["score"], 60)
        self.assertLess(mid_q["score"], 80)
        self.assertEqual(mid_q["verdict"], "adequate")
        self.assertIsNone(engine.encoding_quality("missing-id"))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "encoding_quality", {"memory_id": good.id}
        )
        self.assertEqual(via_mcp["verdict"], "well_encoded")

    def test_explain_memory(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        m1 = engine.remember(
            "explained memory one",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["explain-a"],
            auto_cues=False,
        )
        m2 = engine.remember(
            "explained memory two",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["explain-b"],
            auto_cues=False,
        )
        m3 = engine.remember(
            "explained memory three",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["explain-c"],
            auto_cues=False,
        )
        engine.backend.add_link(m1.id, m3.id)
        engine.backend.add_link(m3.id, m1.id)
        for _ in range(3):
            m1.touch()
        engine.backend.update(m1)
        engine.suppress_memories([m2.id])
        e1 = engine.explain_memory(m1.id)
        self.assertGreaterEqual(e1["linked_count"], 1)
        self.assertEqual(e1["access_count"], 3)
        self.assertFalse(e1["suppressed"])
        e2 = engine.explain_memory(m2.id)
        self.assertEqual(e2["linked_count"], 0)
        self.assertTrue(e2["suppressed"])
        e3 = engine.explain_memory(m3.id)
        self.assertIn("retrievability", e3)
        self.assertIn("review_streak", e3)
        self.assertIsNone(engine.explain_memory("missing-id"))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "explain_memory", {"memory_id": m1.id}
        )
        self.assertEqual(via_mcp["access_count"], 3)

    def test_compare_memories(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        dup_a = engine.remember(
            "alpha shared beta value",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["dup-key"],
            auto_cues=False,
        )
        dup_b = engine.remember(
            "alpha shared beta values",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["dup-key"],
            auto_cues=False,
        )
        con_a = engine.remember(
            "aaa conflict one",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["conflict-key"],
            auto_cues=False,
        )
        con_b = engine.remember(
            "bbb conflict two",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["conflict-key"],
            auto_cues=False,
        )
        dis_a = engine.remember(
            "zzz alpha m", kind=MemoryKind.SEMANTIC, source=user,
            cues=["dis-a"], auto_cues=False,
        )
        dis_b = engine.remember(
            "qqq beta n", kind=MemoryKind.SEMANTIC, source=user,
            cues=["dis-b"], auto_cues=False,
        )
        dup = engine.compare_memories(dup_a.id, dup_b.id)
        self.assertEqual(dup["verdict"], "duplicate")
        self.assertGreaterEqual(dup["overlap"], 0.6)
        con = engine.compare_memories(con_a.id, con_b.id)
        self.assertEqual(con["verdict"], "conflict")
        self.assertIn("conflict-key", con["shared_cues"])
        dis = engine.compare_memories(dis_a.id, dis_b.id)
        self.assertEqual(dis["verdict"], "distinct")
        self.assertEqual(dis["overlap"], 0.0)
        self.assertIn("common_terms", dup)
        self.assertIsNone(engine.compare_memories(dup_a.id, "missing"))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "compare_memories", {"id_a": dup_a.id, "id_b": dup_b.id}
        )
        self.assertEqual(via_mcp["verdict"], "duplicate")

    def test_action_queue(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        now = utcnow()
        i1 = engine.remember_intent("soon a", due_at=now + timedelta(minutes=10))
        i2 = engine.remember_intent("soon b", due_at=now + timedelta(minutes=20))
        i3 = engine.remember_intent("later", due_at=now + timedelta(hours=2))
        i4 = engine.remember_intent("overdue", due_at=now - timedelta(hours=1))
        i5 = engine.remember_intent(
            "office a", due_at=now + timedelta(days=1), context_cue="office"
        )
        i6 = engine.remember_intent(
            "office b", due_at=now + timedelta(days=2), context_cue="office"
        )
        queue = engine.action_queue(now=now)
        self.assertEqual(queue["total"], 6)
        self.assertEqual(queue["overdue"], 1)
        self.assertEqual(queue["actions"][0]["intent_id"], i4["id"])
        by_id = {a["intent_id"]: a for a in queue["actions"]}
        self.assertTrue(by_id[i1["id"]]["urgent"])
        self.assertFalse(by_id[i3["id"]]["urgent"])
        self.assertTrue(by_id[i1["id"]]["clash"])
        self.assertTrue(by_id[i6["id"]]["clash"])
        self.assertFalse(by_id[i3["id"]]["clash"])
        self.assertEqual(queue["clashes"], 4)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("action_queue", {"limit": 10})
        self.assertEqual(via_mcp["total"], 6)
        self.assertEqual(via_mcp["overdue"], 1)

    def test_summarize_cluster(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        ids = []
        for text in (
            "会议讨论预算方案A",
            "会议讨论预算方案B",
            "邮件确认预算方案C",
            "文档记录预算方案D",
        ):
            item = engine.remember(
                text,
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["工作"],
                auto_cues=False,
            )
            ids.append(item.id)
        report = engine.summarize_cluster(ids)
        self.assertEqual(len(report["memory_ids"]), 4)
        self.assertIn("工作", report["common_cues"])
        self.assertIn("预算", report["top_terms"])
        self.assertTrue(report["summary"])
        self.assertEqual(report["evidence_count"], 4)
        self.assertGreater(report["total_chars"], 0)
        self.assertEqual(len(report["previews"]), 4)
        self.assertIsNone(engine.summarize_cluster(["missing-id"]))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "summarize_cluster", {"memory_ids": ids}
        )
        self.assertEqual(len(via_mcp["memory_ids"]), 4)
        self.assertIn("预算", via_mcp["top_terms"])

    def test_multi_hop_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        items = [
            engine.remember(
                f"zzz {letter}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"mh-{letter}"],
                auto_cues=False,
            )
            for letter in ("a", "b", "c", "d", "e")
        ]
        a, b, c, d, e = [item.id for item in items]
        engine.backend.add_link(a, b)
        engine.backend.add_link(b, c)
        engine.backend.add_link(c, d)
        engine.backend.add_link(b, e)
        report = engine.multi_hop_report(a, depth=2)
        self.assertEqual(report["hops"][0]["memory_ids"], [b])
        self.assertEqual(
            set(report["hops"][1]["memory_ids"]), {c, e}
        )
        self.assertEqual(report["total_reached"], 3)
        deep = engine.multi_hop_report(a, depth=3)
        self.assertEqual(
            set(deep["hops"][2]["memory_ids"]), {d}
        )
        self.assertEqual(deep["total_reached"], 4)
        self.assertIsNone(engine.multi_hop_report("missing-id"))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "multi_hop_report", {"start_id": a, "depth": 2}
        )
        self.assertEqual(via_mcp["total_reached"], 3)

    def test_cramming_plan(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        high_ids = []
        low_ids = []
        for i in range(3):
            item = engine.remember(
                f"zzz high {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"ch-{i}"],
                importance=0.9,
                auto_cues=False,
            )
            high_ids.append(item.id)
        for i in range(3):
            item = engine.remember(
                f"zzz low {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"cl-{i}"],
                importance=0.3,
                auto_cues=False,
            )
            low_ids.append(item.id)
        target = utcnow() + timedelta(hours=3)
        plan = engine.cramming_plan(
            target_at=target,
            hours_available=2.0,
            session_minutes=30,
            limit=6,
        )
        self.assertEqual(plan["total_memories"], 6)
        self.assertEqual(len(plan["sessions"]), 4)
        self.assertEqual(
            sum(s["count"] for s in plan["sessions"]), 6
        )
        first_ids = set(plan["sessions"][0]["memory_ids"])
        self.assertTrue(first_ids & set(high_ids))
        self.assertIn("target_at", plan)
        self.assertIn("hours_available", plan)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "cramming_plan",
            {"target_at": target.isoformat(), "hours_available": 2},
        )
        self.assertEqual(via_mcp["total_memories"], 6)
        self.assertEqual(len(via_mcp["sessions"]), 4)

    def test_session_summary(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        ids = []
        for text, cue in (
            ("fact alpha", "ss-a"),
            ("fact beta", "ss-b"),
            ("event one", "ss-e1"),
            ("event two", "ss-e2"),
            ("zzz conflict one", "session-conflict"),
            ("qqq conflict two", "session-conflict"),
        ):
            item = engine.remember(
                text,
                kind=(
                    MemoryKind.SEMANTIC
                    if text.startswith(("fact", "zzz", "qqq"))
                    else MemoryKind.EPISODIC
                ),
                source=user,
                cues=[cue],
                confidence=0.8 if cue == "session-conflict" else 1.0,
                auto_cues=False,
            )
            ids.append(item.id)
        summary = engine.session_summary(ids)
        self.assertEqual(summary["total"], 6)
        self.assertEqual(len(summary["facts"]), 4)
        self.assertEqual(len(summary["events"]), 2)
        self.assertEqual(len(summary["conflicts"]), 1)
        self.assertEqual(len(summary["duplicates"]), 0)
        self.assertTrue(summary["summary"])
        self.assertIsNone(engine.session_summary(["missing-id"]))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "session_summary", {"memory_ids": ids}
        )
        self.assertEqual(via_mcp["total"], 6)
        self.assertEqual(len(via_mcp["conflicts"]), 1)

    def test_topic_drift_report(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        for i in range(3):
            engine.remember(
                f"drift work old {i}",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=["工作"],
                created_at=now - timedelta(days=40, hours=i),
                auto_cues=False,
            )
        engine.remember(
            "drift life old", kind=MemoryKind.EPISODIC, source=user,
            cues=["生活"], created_at=now - timedelta(days=40),
            auto_cues=False,
        )
        engine.remember(
            "drift work new", kind=MemoryKind.EPISODIC, source=user,
            cues=["工作"], created_at=now - timedelta(days=8),
            auto_cues=False,
        )
        for i in range(2):
            engine.remember(
                f"drift life new {i}",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=["生活"],
                created_at=now - timedelta(days=8, hours=i),
                auto_cues=False,
            )
        for i in range(2):
            engine.remember(
                f"drift trip new {i}",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=["旅行"],
                created_at=now - timedelta(days=8, hours=i),
                auto_cues=False,
            )
        report = engine.topic_drift_report(period_days=30)
        self.assertEqual(len(report["periods"]), 2)
        by_topic = {t["topic"]: t for t in report["topics"]}
        self.assertIn("工作", by_topic)
        self.assertIn("生活", by_topic)
        self.assertIn("旅行", by_topic)
        self.assertEqual(by_topic["工作"]["delta"], -2)
        self.assertEqual(by_topic["工作"]["status"], "shrank")
        self.assertEqual(by_topic["生活"]["delta"], 1)
        self.assertEqual(by_topic["生活"]["status"], "grew")
        self.assertEqual(by_topic["旅行"]["delta"], 2)
        self.assertEqual(by_topic["旅行"]["status"], "new")
        self.assertEqual(report["total_drift"], 3)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "topic_drift_report", {"period_days": 30}
        )
        self.assertEqual(via_mcp["total_drift"], 3)

    def test_forgetting_export(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        m1 = engine.remember(
            "forget strong", kind=MemoryKind.SEMANTIC, source=user,
            cues=["fg-1"], strength=1.0, auto_cues=False,
        )
        m2 = engine.remember(
            "forget weak", kind=MemoryKind.SEMANTIC, source=user,
            cues=["fg-2"], strength=0.3, auto_cues=False,
        )
        curve1 = engine.forgetting_export(m1.id, days=30)
        self.assertEqual(len(curve1["points"]), 31)
        self.assertEqual(curve1["points"][0]["days_from_now"], 0)
        self.assertEqual(curve1["points"][-1]["days_from_now"], 30)
        self.assertLess(curve1["final"], curve1["initial"])
        self.assertTrue(
            all(
                curve1["points"][i]["retrievability"]
                >= curve1["points"][i + 1]["retrievability"]
                for i in range(len(curve1["points"]) - 1)
            )
        )
        curve2 = engine.forgetting_export(m2.id, days=30)
        self.assertLess(curve2["final"], curve1["final"])
        self.assertIsNone(engine.forgetting_export("missing-id"))
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "forgetting_export", {"memory_id": m1.id, "days": 30}
        )
        self.assertEqual(len(via_mcp["points"]), 31)
        self.assertIn("initial", via_mcp)

    def test_coverage_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)

        def _add(topic: str, n: int, reviewed: int) -> None:
            for i in range(n):
                item = engine.remember(
                    f"cov {topic} {i}",
                    kind=MemoryKind.SEMANTIC,
                    source=user,
                    cues=[topic],
                    auto_cues=False,
                )
                if i < reviewed:
                    item.retrieval_successes = 1
                    engine.backend.update(item)

        _add("主题甲", 4, 3)
        _add("主题乙", 4, 1)
        _add("主题丙", 2, 0)
        report = engine.coverage_report()
        self.assertEqual(report["total_topics"], 3)
        by_topic = {t["topic"]: t for t in report["topics"]}
        self.assertEqual(by_topic["主题甲"]["coverage"], 0.75)
        self.assertEqual(by_topic["主题甲"]["status"], "good")
        self.assertEqual(by_topic["主题乙"]["coverage"], 0.25)
        self.assertEqual(by_topic["主题乙"]["status"], "partial")
        self.assertEqual(by_topic["主题丙"]["coverage"], 0.0)
        self.assertEqual(by_topic["主题丙"]["status"], "unreviewed")
        self.assertEqual(by_topic["主题甲"]["reviewed_count"], 3)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("coverage_report", {"limit": 10})
        self.assertEqual(via_mcp["total_topics"], 3)

    def test_source_calibration(self) -> None:
        engine = MemoryEngine()

        def _remember(text: str, origin: SourceType, trust: float,
                      confidence: float, evidence: int,
                      importance: float) -> None:
            engine.remember(
                text,
                kind=MemoryKind.SEMANTIC,
                source=SourceRecord(
                    origin=origin, trust=trust
                ),
                cues=[f"sc-{text}"],
                confidence=confidence,
                evidence_count=evidence,
                importance=importance,
                auto_cues=False,
            )

        _remember("user fact 1", SourceType.USER, 1.0, 1.0, 5, 0.8)
        _remember("user fact 2", SourceType.USER, 1.0, 1.0, 5, 0.8)
        _remember("agent fact 1", SourceType.AGENT, 0.5, 0.6, 1, 0.4)
        _remember("agent fact 2", SourceType.AGENT, 0.5, 0.6, 1, 0.4)
        _remember("doc fact 1", SourceType.DOCUMENT, 0.9, 0.9, 3, 0.7)
        _remember("doc fact 2", SourceType.DOCUMENT, 0.9, 0.9, 3, 0.7)
        report = engine.source_calibration()
        self.assertEqual(report["total_memories"], 6)
        by_origin = {s["origin"]: s for s in report["sources"]}
        self.assertEqual(set(by_origin), {"user", "agent", "document"})
        self.assertGreater(
            by_origin["user"]["trust_score"],
            by_origin["agent"]["trust_score"],
        )
        self.assertEqual(by_origin["user"]["avg_confidence"], 1.0)
        self.assertEqual(by_origin["user"]["avg_evidence"], 5.0)
        self.assertEqual(by_origin["user"]["memory_count"], 2)
        self.assertEqual(report["sources"][0]["origin"], "user")
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("source_calibration", {})
        self.assertEqual(via_mcp["total_memories"], 6)
        self.assertEqual(via_mcp["sources"][0]["origin"], "user")

    def test_forgetting_risk(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        for i in range(2):
            engine.remember(
                f"old important {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"fr-oi{i}"],
                importance=0.9,
                created_at=now - timedelta(days=30),
                auto_cues=False,
            )
        for i in range(2):
            engine.remember(
                f"new trivial {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"fr-nt{i}"],
                importance=0.2,
                created_at=now - timedelta(days=1),
                auto_cues=False,
            )
        report = engine.forgetting_risk(now=now)
        self.assertEqual(report["total"], 4)
        self.assertTrue(
            all(
                report["riskiest"][i]["risk"]
                >= report["riskiest"][i + 1]["risk"]
                for i in range(len(report["riskiest"]) - 1)
            )
        )
        first = report["riskiest"][0]
        self.assertEqual(first["importance"], 0.9)
        self.assertLess(first["retrievability"], 0.9)
        self.assertAlmostEqual(
            first["risk"],
            round(first["importance"] * (1 - first["retrievability"]), 3),
        )
        self.assertGreater(report["avg_risk"], 0.0)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("forgetting_risk", {"limit": 5})
        self.assertEqual(via_mcp["total"], 4)
        self.assertEqual(via_mcp["riskiest"][0]["importance"], 0.9)

    def test_bridge_suggestions(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        a = engine.remember(
            "bridge alpha", kind=MemoryKind.SEMANTIC, source=user,
            cues=["共同"], auto_cues=False,
        )
        b = engine.remember(
            "bridge beta", kind=MemoryKind.SEMANTIC, source=user,
            cues=["temp-b"], auto_cues=False,
        )
        b.cues = ["共同"]
        engine.backend.update(b)
        c = engine.remember(
            "bridge gamma", kind=MemoryKind.SEMANTIC, source=user,
            cues=["也共同"], auto_cues=False,
        )
        d = engine.remember(
            "bridge delta", kind=MemoryKind.SEMANTIC, source=user,
            cues=["temp-d"], auto_cues=False,
        )
        d.cues = ["也共同"]
        engine.backend.update(d)
        e = engine.remember(
            "bridge epsilon", kind=MemoryKind.SEMANTIC, source=user,
            cues=["已有"], auto_cues=False,
        )
        f = engine.remember(
            "bridge zeta", kind=MemoryKind.SEMANTIC, source=user,
            cues=["temp-f"], auto_cues=False,
        )
        f.cues = ["已有"]
        engine.backend.update(f)
        engine.backend.add_link(e.id, f.id)
        engine.backend.add_link(f.id, e.id)
        report = engine.bridge_suggestions(limit=10)
        self.assertEqual(report["total"], 2)
        pairs = {
            frozenset((s["id_a"], s["id_b"]))
            for s in report["suggestions"]
        }
        self.assertIn(frozenset((a.id, b.id)), pairs)
        self.assertIn(frozenset((c.id, d.id)), pairs)
        self.assertNotIn(frozenset((e.id, f.id)), pairs)
        ab = next(
            s for s in report["suggestions"]
            if {s["id_a"], s["id_b"]} == {a.id, b.id}
        )
        self.assertEqual(ab["shared_cues"], ["共同"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("bridge_suggestions", {"limit": 10})
        self.assertEqual(via_mcp["total"], 2)

    def test_plan_quality(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        ctx = engine.remember(
            "调研需求、架构、开发、测试、部署、上线全部确认",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["项目"],
            auto_cues=False,
        )
        good = engine.plan_quality(
            ["调研需求", "设计架构", "开发功能", "测试功能", "部署上线"],
            context_memory_ids=[ctx.id],
        )
        self.assertGreaterEqual(good["score"], 75)
        self.assertEqual(good["verdict"], "good")
        self.assertTrue(good["has_verbs"])
        self.assertGreater(good["context_alignment"], 0.0)
        weak = engine.plan_quality(["功能", "功能", "完成"])
        self.assertLess(weak["score"], 50)
        self.assertEqual(weak["verdict"], "weak")
        self.assertTrue(weak["duplicate_steps"])
        self.assertTrue(weak["suggestions"])
        empty = engine.plan_quality([])
        self.assertEqual(empty["score"], 0)
        self.assertEqual(empty["verdict"], "empty")
        self.assertEqual(empty["step_count"], 0)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "plan_quality",
            {
                "plan": ["调研需求", "设计架构", "开发功能", "测试功能", "部署上线"],
                "context_memory_ids": [ctx.id],
            },
        )
        self.assertEqual(via_mcp["verdict"], "good")

    def test_project_brief(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        ids = []
        for text, cue in (
            ("项目关于智能客服机器人", "pb-1"),
            ("需求：支持中文多轮对话", "pb-2"),
            ("风险：模型延迟高", "pb-3"),
            ("记录了会议纪要", "pb-4"),
        ):
            item = engine.remember(
                text,
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[cue],
                auto_cues=False,
            )
            ids.append(item.id)
        engine.remember_intent(
            "交付客服项目", due_at=utcnow() - timedelta(hours=1)
        )
        brief = engine.project_brief("智能客服", memory_ids=ids)
        self.assertFalse(brief["empty"])
        self.assertEqual(len(brief["background"]), 4)
        req_ids = {r["id"] for r in brief["requirements"]}
        self.assertIn(ids[1], req_ids)
        risk_ids = {r["id"] for r in brief["risks"]}
        self.assertIn(ids[2], risk_ids)
        self.assertGreaterEqual(len(brief["pending_actions"]), 1)
        self.assertTrue(brief["summary"])
        self.assertTrue(
            engine.project_brief("无记忆", memory_ids=["missing-id"])["empty"]
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "project_brief", {"title": "智能客服", "memory_ids": ids}
        )
        self.assertEqual(len(via_mcp["background"]), 4)
        self.assertGreaterEqual(len(via_mcp["pending_actions"]), 1)

    def test_numeric_reasoning(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        ctx = engine.remember(
            "汽车速度 60 千米每小时",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["速度"],
            auto_cues=False,
        )
        consistent = engine.numeric_reasoning(
            "汽车3小时行驶180千米",
            context_memory_ids=[ctx.id],
        )
        self.assertEqual(consistent["verdict"], "consistent")
        self.assertTrue(
            any(
                check["type"] == "memory_consistency"
                and check["ok"]
                for check in consistent["checks"]
            )
        )
        mixed = engine.numeric_reasoning("绳子长2米，又接上3公里")
        self.assertEqual(mixed["verdict"], "review_needed")
        self.assertTrue(
            any(check["type"] == "unit_mix" for check in mixed["checks"])
        )
        zero = engine.numeric_reasoning("把10元除以0个人")
        self.assertEqual(zero["verdict"], "review_needed")
        self.assertTrue(
            any(
                check["type"] == "zero_division"
                for check in zero["checks"]
            )
        )
        self.assertEqual(
            [entry["value"] for entry in consistent["numbers"]],
            [3.0, 180.0],
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "numeric_reasoning",
            {
                "problem": "汽车3小时行驶180千米",
                "context_memory_ids": [ctx.id],
            },
        )
        self.assertEqual(via_mcp["verdict"], "consistent")

    def test_plan_support(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        m1 = engine.remember(
            "需求文档已确认", kind=MemoryKind.SEMANTIC, source=user,
            cues=["需求"], auto_cues=False,
        )
        m2 = engine.remember(
            "上线检查清单", kind=MemoryKind.SEMANTIC, source=user,
            cues=["上线"], auto_cues=False,
        )
        report = engine.plan_support(["调研需求", "部署上线"], top_k=3)
        self.assertEqual(len(report["steps"]), 2)
        self.assertGreaterEqual(report["steps"][0]["support_count"], 1)
        self.assertGreaterEqual(report["steps"][1]["support_count"], 1)
        self.assertIn(
            "需求", report["steps"][0]["support"][0]["preview"]
        )
        self.assertIn(
            "上线", report["steps"][1]["support"][0]["preview"]
        )
        self.assertEqual(report["total_supported"], 2)
        self.assertTrue(
            all(
                entry["support"][i]["score"]
                >= entry["support"][i + 1]["score"]
                for entry in report["steps"]
                for i in range(len(entry["support"]) - 1)
            )
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "plan_support", {"plan": ["调研需求", "部署上线"]}
        )
        self.assertEqual(via_mcp["total_supported"], 2)
        self.assertEqual(len(via_mcp["steps"]), 2)

    def test_dependency_map(self) -> None:
        engine = MemoryEngine()
        plan = [
            {"step": "调研需求", "depends_on": []},
            {"step": "设计架构", "depends_on": [0]},
            {"step": "开发功能", "depends_on": [1]},
            {"step": "测试功能", "depends_on": [2]},
            {"step": "部署上线", "depends_on": [3]},
            {"step": "写文档", "depends_on": [1]},
        ]
        report = engine.dependency_map(plan)
        self.assertEqual(len(report["steps"]), 6)
        by_index = {s["index"]: s for s in report["steps"]}
        self.assertEqual(by_index[2]["depends_on"], [1])
        self.assertEqual(
            [s["level"] for s in report["steps"]],
            [0, 1, 2, 3, 4, 2],
        )
        self.assertTrue(
            any(
                group["level"] == 2
                and set(group["step_indices"]) == {2, 5}
                for group in report["parallel_groups"]
            )
        )
        self.assertEqual(
            [s["index"] for s in report["critical_path"]],
            [0, 1, 2, 3, 4],
        )
        self.assertEqual(report["finish_level"], 4)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("dependency_map", {"plan": plan})
        self.assertEqual(len(via_mcp["critical_path"]), 5)
        self.assertEqual(via_mcp["finish_level"], 4)

    def test_project_risk(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        ids = []
        for text, cue in (
            ("风险：模型延迟高", "pr-1"),
            ("注意：数据权限未确认", "pr-2"),
            ("需求：支持中文多轮对话", "pr-3"),
            ("记录了会议纪要", "pr-4"),
            ("aaa conflict one", "conflict-key"),
            ("bbb conflict two", "conflict-key"),
        ):
            item = engine.remember(
                text,
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[cue],
                confidence=0.8 if cue == "conflict-key" else 1.0,
                auto_cues=False,
            )
            ids.append(item.id)
        engine.remember_intent(
            "overdue task", due_at=now - timedelta(hours=1)
        )
        engine.remember_intent(
            "clash a", due_at=now + timedelta(minutes=10)
        )
        engine.remember_intent(
            "clash b", due_at=now + timedelta(minutes=20)
        )
        report = engine.project_risk(memory_ids=ids)
        self.assertEqual(report["risk_score"], 70)
        self.assertEqual(report["verdict"], "high")
        self.assertEqual(
            report["factors"],
            {
                "risk_memories": 2,
                "conflicts": 1,
                "overdue_intents": 1,
                "intent_clashes": 2,
            },
        )
        self.assertTrue(report["suggestions"])
        self.assertGreaterEqual(len(report["risk_memory_previews"]), 2)
        empty = MemoryEngine().project_risk()
        self.assertEqual(empty["risk_score"], 0)
        self.assertEqual(empty["verdict"], "low")
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "project_risk", {"memory_ids": ids}
        )
        self.assertEqual(via_mcp["verdict"], "high")
        self.assertEqual(via_mcp["risk_score"], 70)

    def test_plan_tracker(self) -> None:
        engine = MemoryEngine()
        plan = ["调研需求", "设计架构", "开发功能", "测试功能"]
        statuses = {
            "0": "done",
            "1": "in_progress",
            "2": "blocked",
            "3": "pending",
        }
        report = engine.plan_tracker(plan, statuses=statuses)
        self.assertEqual(report["total"], 4)
        self.assertEqual(
            [s["status"] for s in report["steps"]],
            ["done", "in_progress", "blocked", "pending"],
        )
        self.assertEqual(
            report["progress"],
            {"pending": 1, "in_progress": 1, "done": 1, "blocked": 1},
        )
        self.assertEqual(report["completion_ratio"], 0.25)
        default = engine.plan_tracker(plan)
        self.assertEqual(
            set(s["status"] for s in default["steps"]),
            {"pending"},
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "plan_tracker", {"plan": plan, "statuses": statuses}
        )
        self.assertEqual(via_mcp["completion_ratio"], 0.25)
        self.assertEqual(via_mcp["total"], 4)

    def test_plan_rewrite(self) -> None:
        engine = MemoryEngine()
        report = engine.plan_rewrite(["功能", "部署", "功能", "需求"])
        self.assertEqual(len(report["original"]), 4)
        self.assertEqual(
            report["rewritten"],
            ["调研需求", "开发功能", "部署上线"],
        )
        self.assertTrue(
            all(
                any(verb in step for verb in engine._PLAN_VERBS)
                for step in report["rewritten"]
            )
        )
        self.assertTrue(report["changes"])
        self.assertEqual(engine.plan_rewrite([])["rewritten"], [])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "plan_rewrite", {"plan": ["功能", "部署", "功能", "需求"]}
        )
        self.assertEqual(
            via_mcp["rewritten"],
            ["调研需求", "开发功能", "部署上线"],
        )

    def test_lesson_learned(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        ids = []
        for text, cue in (
            ("上线成功，客户满意", "ll-1"),
            ("测试失败，超时严重", "ll-2"),
            ("经验：先做原型再开发", "ll-3"),
            ("记录了会议纪要", "ll-4"),
        ):
            item = engine.remember(
                text,
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[cue],
                auto_cues=False,
            )
            ids.append(item.id)
        report = engine.lesson_learned(memory_ids=ids)
        self.assertEqual(report["total"], 3)
        self.assertEqual(
            report["tags"],
            {"success": 1, "failure": 1, "lesson": 1},
        )
        self.assertTrue(all(item["preview"] for item in report["lessons"]))
        lesson_ids = {item["id"] for item in report["lessons"]}
        self.assertNotIn(ids[3], lesson_ids)
        self.assertEqual(
            MemoryEngine().lesson_learned()["total"], 0
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "lesson_learned", {"memory_ids": ids}
        )
        self.assertEqual(via_mcp["total"], 3)
        self.assertEqual(via_mcp["tags"]["success"], 1)

    def test_effort_estimate(self) -> None:
        engine = MemoryEngine()
        plan = [
            {"step": "调研需求", "depends_on": []},
            {"step": "设计架构", "depends_on": [0]},
            {"step": "开发功能", "depends_on": [1]},
            {"step": "测试功能", "depends_on": [2]},
            {"step": "部署上线", "depends_on": [3]},
        ]
        report = engine.effort_estimate(plan)
        self.assertEqual(len(report["steps"]), 5)
        self.assertTrue(
            all(entry["estimated_hours"] > 0 for entry in report["steps"])
        )
        self.assertEqual(report["total_hours"], 26.0)
        self.assertEqual(report["critical_path_hours"], 26.0)
        self.assertEqual(report["buffered_total_hours"], 31.2)
        self.assertTrue(report["note"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("effort_estimate", {"plan": plan})
        self.assertEqual(via_mcp["total_hours"], 26.0)
        self.assertEqual(via_mcp["buffered_total_hours"], 31.2)

    def test_decision_review(self) -> None:
        engine = MemoryEngine()
        plan = ["调研需求", "设计架构", "开发功能", "测试功能"]
        results = {
            "0": {"status": "success"},
            "1": {"status": "success"},
            "2": {"status": "failure", "note": "超时"},
            "3": {"status": "unknown"},
        }
        report = engine.decision_review(plan, results)
        self.assertEqual(report["total_steps"], 4)
        self.assertEqual(report["success_rate"], 0.5)
        self.assertEqual(report["score"], 50)
        self.assertEqual(report["verdict"], "fair")
        self.assertEqual(
            report["patterns"]["success_steps"],
            ["调研需求", "设计架构"],
        )
        self.assertEqual(
            report["patterns"]["failure_steps"], ["开发功能"]
        )
        self.assertTrue(
            any("开发功能" in lesson["text"] for lesson in report["lessons"])
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "decision_review", {"plan": plan, "results": results}
        )
        self.assertEqual(via_mcp["score"], 50)
        self.assertEqual(via_mcp["verdict"], "fair")

    def test_transfer_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        ids = []
        for text, cue in (
            ("成功：先调研需求再开发", "tr-1"),
            ("失败：测试超时", "tr-2"),
            ("经验：原型先行", "tr-3"),
        ):
            item = engine.remember(
                text,
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[cue],
                auto_cues=False,
            )
            ids.append(item.id)
        report = engine.transfer_report(
            ["调研需求", "开发功能", "测试功能"],
            lessons_memory_ids=ids,
        )
        self.assertEqual(len(report["plan_steps"]), 3)
        self.assertEqual(report["total_lessons"], 3)
        self.assertEqual(len(report["applicable_lessons"]), 2)
        by_id = {lesson["id"]: lesson for lesson in report["applicable_lessons"]}
        self.assertIn("调研需求", by_id[ids[0]]["matched_steps"])
        self.assertIn("测试功能", by_id[ids[1]]["matched_steps"])
        self.assertNotIn(ids[2], by_id)
        self.assertTrue(report["suggestion"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "transfer_report",
            {"plan": ["调研需求", "开发功能", "测试功能"],
             "lessons_memory_ids": ids},
        )
        self.assertEqual(len(via_mcp["applicable_lessons"]), 2)

    def test_retrieval_quality(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for i in range(4):
            engine.remember(
                f"quality item {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"rq-{i}"],
                auto_cues=False,
            )
        report = engine.retrieval_quality(
            queries=["rq-0", "rq-1", "rq-2", "rq-3", "zzz miss", "qqq miss"],
            top_k=3,
        )
        self.assertEqual(report["queries_evaluated"], 6)
        self.assertGreaterEqual(report["hit_count"], 4)
        self.assertGreaterEqual(report["weak_count"], 1)
        self.assertTrue(0.0 <= report["hit_rate"] <= 1.0)
        self.assertIn(
            report["verdict"], ("good", "fair", "poor")
        )
        self.assertIn("avg_top_score", report)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "retrieval_quality",
            {"queries": ["rq-0", "rq-1", "zzz miss"], "top_k": 3},
        )
        self.assertEqual(via_mcp["queries_evaluated"], 3)

    def test_recall_trace(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        m1 = engine.remember(
            "trace target memory",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["trace-key"],
            auto_cues=False,
        )
        engine.remember(
            "trace distractor one",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["trace-d1"],
            auto_cues=False,
        )
        engine.remember(
            "trace distractor two",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["trace-d2"],
            auto_cues=False,
        )
        trace = engine.recall_trace("trace-key", top_k=3)
        self.assertGreaterEqual(trace["candidates_scanned"], 3)
        self.assertEqual(trace["results"][0]["id"], m1.id)
        self.assertTrue(
            any(
                "overlap" in reason
                for reason in trace["results"][0]["reasons"]
            )
        )
        self.assertTrue(trace["results"][0]["confident"])
        self.assertTrue(trace["top_reason_summary"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "recall_trace", {"query": "trace-key", "top_k": 3}
        )
        self.assertEqual(via_mcp["results"][0]["id"], m1.id)
        self.assertGreaterEqual(via_mcp["candidates_scanned"], 3)

    def test_community_report(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for name in ("a1", "a2", "a3", "a4"):
            engine.remember(
                f"zzz {name}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["社区A"],
                auto_cues=False,
            )
        for name in ("b1", "b2"):
            engine.remember(
                f"zzz {name}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["社区B"],
                auto_cues=False,
            )
        engine.remember(
            "zzz c1", kind=MemoryKind.SEMANTIC, source=user,
            cues=["独一"], auto_cues=False,
        )
        engine.remember(
            "zzz c2", kind=MemoryKind.SEMANTIC, source=user,
            cues=["独二"], auto_cues=False,
        )
        report = engine.community_report()
        self.assertEqual(report["total_communities"], 4)
        self.assertEqual(report["largest_size"], 4)
        sizes = sorted(c["size"] for c in report["communities"])
        self.assertEqual(sizes, [1, 1, 2, 4])
        community_a = next(c for c in report["communities"] if c["size"] == 4)
        self.assertIn("社区a", community_a["top_cues"])
        self.assertTrue(
            all(c["members"] for c in report["communities"])
        )
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("community_report", {"limit": 10})
        self.assertEqual(via_mcp["largest_size"], 4)
        self.assertEqual(via_mcp["total_communities"], 4)

    def test_sleep_advice(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        engine.remember(
            "sleep weak important",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["sw-1"],
            importance=0.8,
            created_at=now - timedelta(days=30),
            auto_cues=False,
        )
        engine.remember(
            "zzz conflict one", kind=MemoryKind.SEMANTIC, source=user,
            cues=["sleep-conflict"], confidence=0.8, auto_cues=False,
        )
        engine.remember(
            "zzz conflict two", kind=MemoryKind.SEMANTIC, source=user,
            cues=["sleep-conflict"], confidence=0.8, auto_cues=False,
        )
        for i in range(2):
            engine.remember(
                f"blind topic {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["盲区主题"],
                auto_cues=False,
            )
        engine.remember_intent(
            "sleep overdue", due_at=now - timedelta(hours=1)
        )
        report = engine.sleep_advice(now=now)
        self.assertGreaterEqual(len(report["pre_sleep_review"]), 1)
        self.assertGreaterEqual(report["conflicts_to_resolve"], 1)
        self.assertGreaterEqual(report["overdue_intents"], 1)
        self.assertTrue(report["tomorrow_priorities"])
        self.assertTrue(
            any(
                topic["topic"] == "盲区主题"
                for topic in report["tomorrow_priorities"]
            )
        )
        self.assertTrue(report["advice"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("sleep_advice", {})
        self.assertGreaterEqual(len(via_mcp["pre_sleep_review"]), 1)
        self.assertGreaterEqual(via_mcp["conflicts_to_resolve"], 1)

    def test_emotion_advice(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for i in range(3):
            engine.remember(
                f"happy memory {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["快乐"],
                affect="positive",
                auto_cues=False,
            )
        engine.remember(
            "failed launch", kind=MemoryKind.SEMANTIC, source=user,
            cues=["失败项目"], affect="negative", auto_cues=False,
        )
        engine.remember(
            "missed deadline", kind=MemoryKind.SEMANTIC, source=user,
            cues=["失败项目"], affect="negative", auto_cues=False,
        )
        engine.remember(
            "bad review", kind=MemoryKind.SEMANTIC, source=user,
            cues=["差评"], affect="negative", auto_cues=False,
        )
        for i in range(2):
            engine.remember(
                f"plain note {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"普通{i}"],
                affect="neutral",
                auto_cues=False,
            )
        report = engine.emotion_advice()
        self.assertEqual(report["total_memories"], 8)
        self.assertEqual(
            report["mood_profile"],
            {
                "positive": 3,
                "negative": 3,
                "neutral": 2,
                "arousing": 0,
                "mixed": 0,
            },
        )
        self.assertEqual(report["negative_ratio"], 0.375)
        self.assertTrue(
            any(
                topic["topic"] == "失败项目"
                and topic["negative_count"] == 2
                for topic in report["flagged_topics"]
            )
        )
        self.assertTrue(report["advice"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("emotion_advice", {})
        self.assertEqual(via_mcp["negative_ratio"], 0.375)
        self.assertEqual(via_mcp["mood_profile"]["negative"], 3)

    def test_difficulty_estimator(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for i in range(3):
            engine.remember(
                f"easy fact {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["easy"],
                importance=0.5,
                strength=0.95,
                auto_cues=False,
            )
        engine.remember(
            "sweet formula A",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["math"],
            importance=0.9,
            strength=0.55,
            auto_cues=False,
        )
        engine.remember(
            "sweet formula B",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["math"],
            importance=0.85,
            strength=0.55,
            auto_cues=False,
        )
        engine.remember(
            "hard concept one",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.8,
            strength=0.25,
            auto_cues=False,
        )
        engine.remember(
            "hard concept two",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["化学"],
            importance=0.7,
            strength=0.25,
            auto_cues=False,
        )
        engine.remember(
            "very hard derivation",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.6,
            strength=0.05,
            auto_cues=False,
        )
        report = engine.difficulty_estimator()
        self.assertEqual(report["total_memories"], 8)
        self.assertEqual(
            report["buckets"],
            {"too_easy": 3, "sweet_spot": 2, "hard": 2, "very_hard": 1},
        )
        self.assertEqual(report["sweet_spot_ratio"], 0.25)
        physics = next(
            topic for topic in report["topic_summary"]
            if topic["topic"] == "物理"
        )
        self.assertEqual(physics["hard"], 1)
        self.assertEqual(physics["very_hard"], 1)
        self.assertEqual(report["rows"][0]["importance"], 0.9)
        self.assertTrue(report["advice"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("difficulty_estimator", {})
        self.assertEqual(via_mcp["buckets"]["sweet_spot"], 2)
        self.assertEqual(via_mcp["buckets"]["very_hard"], 1)

    def test_memory_integration(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for i in range(4):
            engine.remember(
                f"physics fact {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["物理"],
                importance=0.7,
                auto_cues=False,
            )
        now = utcnow()
        engine.remember(
            "trip day one",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(
                origin=SourceType.USER,
                occurred_at=now - timedelta(days=2),
            ),
            cues=["旅行"],
            auto_cues=False,
        )
        engine.remember(
            "trip day two",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(
                origin=SourceType.USER,
                occurred_at=now,
            ),
            cues=["旅行"],
            auto_cues=False,
        )
        engine.remember(
            "meeting on monday",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["日期"],
            confidence=0.9,
            auto_cues=False,
        )
        engine.remember(
            "meeting on tuesday",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["日期"],
            confidence=0.9,
            auto_cues=False,
        )
        report = engine.memory_integration()
        physics = next(
            candidate for candidate in report["schema_candidates"]
            if candidate["topic"] == "物理"
        )
        self.assertEqual(physics["count"], 4)
        trip = next(
            chain for chain in report["event_chains"]
            if chain["topic"] == "旅行"
        )
        self.assertEqual(trip["events"], 2)
        self.assertEqual(trip["span_days"], 2.0)
        self.assertGreaterEqual(report["conflicts"], 1)
        self.assertIn("冲突", report["advice"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("memory_integration", {})
        self.assertGreaterEqual(len(via_mcp["schema_candidates"]), 1)
        self.assertGreaterEqual(via_mcp["conflicts"], 1)

    def test_reasoning_trace(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "汽车速度 60 千米每小时",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["速度"],
            auto_cues=False,
        )
        engine.remember(
            "汽车行驶 3 小时",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["时间"],
            auto_cues=False,
        )
        report = engine.reasoning_trace(
            "汽车3小时行驶多少千米", topic="物理"
        )
        self.assertGreaterEqual(len(report["evidence_used"]), 1)
        self.assertTrue(
            any(number["value"] == 3.0 for number in report["numbers"])
        )
        self.assertTrue(
            any(
                number["value"] == 60.0
                for number in report["numbers"]
            )
            or any(
                "60" in item["preview"]
                for item in report["evidence_used"]
            )
        )
        self.assertEqual(len(report["steps"]), 4)
        self.assertTrue(report["stored_memory_id"])
        self.assertIsNotNone(
            engine.backend.get(report["stored_memory_id"])
        )
        stored = engine.backend.get(report["stored_memory_id"])
        self.assertEqual(stored.source.origin, SourceType.INFERENCE)
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "reasoning_trace",
            {"problem": "汽车3小时行驶多少千米", "topic": "物理"},
        )
        self.assertTrue(via_mcp["stored_memory_id"])
        self.assertEqual(len(via_mcp["steps"]), 4)

    def test_goal_replay(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "上次搬家 打包箱子 成功",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["搬家"],
            auto_cues=False,
        )
        engine.remember(
            "上次搬家 找搬家公司 失败",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["搬家"],
            auto_cues=False,
        )
        engine.remember_intent(
            "预约搬家公司", due_at=utcnow() - timedelta(hours=1)
        )
        report = engine.goal_replay("搬家")
        self.assertGreaterEqual(len(report["evidence_used"]), 1)
        self.assertGreaterEqual(report["lessons_found"], 1)
        self.assertGreaterEqual(report["overdue_reactivations"], 1)
        self.assertEqual(
            [step["order"] for step in report["replay_steps"]],
            [1, 2, 3, 4],
        )
        self.assertTrue(0 <= report["replay_score"] <= 1)
        self.assertTrue(report["advice"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool(
            "goal_replay", {"goal": "搬家"}
        )
        self.assertGreaterEqual(via_mcp["lessons_found"], 1)
        self.assertGreaterEqual(via_mcp["overdue_reactivations"], 1)

    def test_sleep_inference(self) -> None:
        from datetime import timedelta

        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        now = utcnow()
        engine.remember(
            "引力使苹果落地",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=20),
            auto_cues=False,
        )
        engine.remember(
            "质量越大引力越大",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=20),
            auto_cues=False,
        )
        report = engine.sleep_inference(limit=5)
        self.assertGreaterEqual(report["total_pairs"], 1)
        self.assertGreaterEqual(report["ready_pairs"], 1)
        top = report["candidates"][0]
        self.assertEqual(top["topic"], "物理")
        self.assertGreaterEqual(top["readiness"], 0.5)
        self.assertTrue(top["reason"])
        self.assertTrue(report["advice"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("sleep_inference", {})
        self.assertGreaterEqual(via_mcp["ready_pairs"], 1)
        self.assertGreaterEqual(via_mcp["total_pairs"], 1)

    def test_schema_fit(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for content in ("物理公式A", "物理公式B", "物理实验C"):
            engine.remember(
                content,
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=["物理"],
                auto_cues=False,
            )
        engine.remember(
            "贝多芬交响曲",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["音乐"],
            auto_cues=False,
        )
        report = engine.schema_fit()
        self.assertEqual(report["total_memories"], 4)
        self.assertEqual(report["schema_count"], 1)
        self.assertTrue(
            any(
                row["verdict"] == "assimilate" and row["topic"] == "物理"
                for row in report["rows"]
            )
        )
        music_row = next(
            row for row in report["rows"] if row["topic"] == "音乐"
        )
        self.assertEqual(music_row["verdict"], "accommodate")
        physics = next(
            schema for schema in report["schema_summary"]
            if schema["topic"] == "物理"
        )
        self.assertEqual(physics["member_count"], 3)
        self.assertGreaterEqual(physics["assimilate"], 1)
        self.assertTrue(report["advice"])
        server = MCPServer(engine=engine)
        via_mcp = server._call_tool("schema_fit", {})
        self.assertEqual(via_mcp["schema_count"], 1)
        self.assertIn("assimilate", via_mcp["verdict_counts"])

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
