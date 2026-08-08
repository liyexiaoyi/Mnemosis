"""Agent project layer tests (round 36: planning / outcomes / MCP tools).

Human principles: prefrontal goal maintenance (Miller & Cohen, 2001),
analogical transfer (Gick & Holyoak, 1980), outcome monitoring and evidence
accumulation (Smolen et al., 2016).
"""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType


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


if __name__ == "__main__":
    unittest.main()
