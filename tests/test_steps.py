"""Chain-of-thought step retrieval (round 31)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _process_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    # inserted out of chronological order on purpose
    steps = [
        ("阿丽在2026年4月3日收拾了行李。", "阿丽", "2026-04-03"),
        ("阿丽在2026年4月5日回到了家。", "阿丽", "2026-04-05"),
        ("阿丽在2026年4月1日订了去京都的机票。", "阿丽", "2026-04-01"),
        ("阿丽在2026年4月4日去了京都。", "阿丽", "2026-04-04"),
        ("阿丽在2026年4月2日买了相机。", "阿丽", "2026-04-02"),
    ]
    for content, person, iso in steps:
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, iso],
        )
    engine.remember(
        "阿丽最喜欢的城市是京都。",
        kind=MemoryKind.SEMANTIC,
        source=source,
        cues=["阿丽", "城市"],
    )
    return engine


class StepRetrievalTests(unittest.TestCase):
    def test_process_question_returns_steps_in_date_order(self) -> None:
        engine = _process_engine()
        results = engine.recall_steps(
            "阿丽是怎么准备去京都旅行的？", top_k=6
        )
        contents = [r.item.content for r in results]
        expected_order = [
            "阿丽在2026年4月1日订了去京都的机票。",
            "阿丽在2026年4月2日买了相机。",
            "阿丽在2026年4月3日收拾了行李。",
            "阿丽在2026年4月4日去了京都。",
            "阿丽在2026年4月5日回到了家。",
        ]
        self.assertEqual(contents[:5], expected_order)

    def test_plain_recall_not_chronologically_sorted(self) -> None:
        engine = _process_engine()
        plain = [r.item.content for r in engine.recall(
            "阿丽是怎么准备去京都旅行的？", top_k=6, reasoning_pack=True
        )]
        self.assertNotEqual(
            plain[:5],
            [
                "阿丽在2026年4月1日订了去京都的机票。",
                "阿丽在2026年4月2日买了相机。",
                "阿丽在2026年4月3日收拾了行李。",
                "阿丽在2026年4月4日去了京都。",
                "阿丽在2026年4月5日回到了家。",
            ],
        )

    def test_non_process_question_unchanged(self) -> None:
        engine = _process_engine()
        q = "阿丽最喜欢的城市是什么？"
        steps = [r.item.content for r in engine.recall_steps(q, top_k=3)]
        plain = [r.item.content for r in engine.recall_reasoning(q, top_k=3)]
        self.assertEqual(steps, plain)

    def test_step_marker_without_how_word(self) -> None:
        engine = _process_engine()
        results = engine.recall_steps(
            "大壮想学阿丽去京都旅行，第一步该做什么？", top_k=6
        )
        contents = [r.item.content for r in results]
        self.assertEqual(
            contents[0],
            "阿丽在2026年4月1日订了去京都的机票。",
        )
        self.assertTrue(
            contents.index("阿丽在2026年4月1日订了去京都的机票。")
            < contents.index("阿丽在2026年4月2日买了相机。")
        )

    def test_plan_reuse_reference_boost(self) -> None:
        engine = _process_engine()
        results = engine.recall_steps(
            "大壮想去京都旅行，参考阿丽是怎么准备的？", top_k=6
        )
        top = results[0]
        self.assertIn("阿丽在2026年4月1日订了去京都的机票。", top.item.content)
        self.assertTrue(
            any("\u7c7b\u6bd4\u8ba1\u5212" in reason for reason in top.reasons)
        )


if __name__ == "__main__":
    unittest.main()
