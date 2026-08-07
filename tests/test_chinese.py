"""Chinese content optimization: stopword filtering + recall (zh)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import (
    MemoryKind,
    SourceRecord,
    SourceType,
    tokenize,
)


class ChineseOptimizationTest(unittest.TestCase):
    def test_chinese_function_words_are_filtered(self) -> None:
        tokens = tokenize("请问阿丽最喜欢的颜色是什么？")
        joined = " ".join(tokens)
        self.assertIn("颜色", tokens)
        self.assertIn("阿丽", tokens)
        for noise in ("请", "问", "的", "最", "什", "么", "是"):
            self.assertNotIn(noise, tokens)
        self.assertNotIn("最喜", tokens)  # bigram spanning a stopword

    def test_zh_fact_recall_with_noisy_query(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "阿丽最喜欢的颜色是琥珀色。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["阿丽", "颜色"],
        )
        results = engine.recall("请问阿丽最喜欢的颜色是什么？", top_k=3)
        self.assertTrue(results)
        self.assertEqual(
            results[0].item.content, "阿丽最喜欢的颜色是琥珀色。"
        )

    def test_zh_event_recall_with_date(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "阿丽在2026年3月1日买了笔记本。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["阿丽", "2026-03-01"],
        )
        engine.remember(
            "阿丽在2026年4月2日去了公园。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["阿丽", "2026-04-02"],
        )
        results = engine.recall("阿丽在2026年3月1日买了什么？", top_k=3)
        self.assertEqual(
            results[0].item.content, "阿丽在2026年3月1日买了笔记本。"
        )


if __name__ == "__main__":
    unittest.main()
