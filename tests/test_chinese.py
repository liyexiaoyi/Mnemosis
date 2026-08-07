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

    def test_cross_format_dates_match(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        # stored with a Chinese date, queried with an ISO date
        engine.remember(
            "阿丽在2026年3月1日买了笔记本。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["阿丽"],
        )
        results = engine.recall("阿丽 2026-03-01", top_k=3)
        self.assertTrue(results)
        self.assertEqual(
            results[0].item.content, "阿丽在2026年3月1日买了笔记本。"
        )
        # stored with an ISO date, queried with a Chinese date
        engine2 = MemoryEngine()
        engine2.remember(
            "小波在2026-04-02买了相机。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["小波"],
        )
        results2 = engine2.recall("小波在2026年4月2日", top_k=3)
        self.assertTrue(results2)
        self.assertEqual(
            results2[0].item.content, "小波在2026-04-02买了相机。"
        )

    def test_chinese_numeral_dates_normalize(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "阿丽在2026年五月二日买了花。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["阿丽"],
        )
        results = engine.recall("阿丽 2026-05-02", top_k=3)
        self.assertTrue(results)
        self.assertEqual(
            results[0].item.content, "阿丽在2026年五月二日买了花。"
        )
        # query side too
        engine2 = MemoryEngine()
        engine2.remember(
            "小波在2026-06-03买了书。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["小波"],
        )
        results2 = engine2.recall("小波在2026年六月三日", top_k=3)
        self.assertTrue(results2)
        self.assertEqual(
            results2[0].item.content, "小波在2026-06-03买了书。"
        )


if __name__ == "__main__":
    unittest.main()
