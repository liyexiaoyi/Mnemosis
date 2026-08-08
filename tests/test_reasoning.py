"""Tests for the reasoning premise pack (round 27)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.reasoning import reasoning_question_kind
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _reasoning_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    memories = [
        # height chain (transitive)
        "阿丽比小波高。",
        "小波比小王高。",
        # price comparison
        "阿丽买相机花了2500元。",
        "小波买手机花了3000元。",
        # unit price math
        "阿丽买了3本笔记本花了90元。",
        "小波买了2本笔记本花了40元。",
        # favorite cities (multi-entity)
        "阿丽最喜欢的城市是成都。",
        "小波最喜欢的城市是杭州。",
        # distractor premises on the same dimensions (other people)
        "琳琳比大壮高。",
        "大壮比强强高。",
        "朵朵买耳机花了200元。",
        "小雨买音箱花了600元。",
        "小雨买了5本笔记本花了150元。",
        "强强买了4本笔记本花了80元。",
        "琳琳最喜欢的城市是西安。",
        "大壮最喜欢的城市是北京。",
    ]
    for content in memories:
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[content.split("比")[0].strip()
                  if "比" in content
                  else content.split("最")[0].strip()
                  if "最" in content
                  else content.split("买")[0].strip()
                  if "买" in content
                  else content.split("喜欢")[0].strip()],
            importance=0.7,
        )
    return engine


class ReasoningKindTests(unittest.TestCase):
    def test_math_kind(self) -> None:
        self.assertEqual(
            reasoning_question_kind("阿丽买的笔记本单价是多少元？"), "math"
        )
        self.assertEqual(
            reasoning_question_kind("阿丽和小波谁花的钱多？差多少元？"), "math"
        )

    def test_compare_kind(self) -> None:
        self.assertEqual(
            reasoning_question_kind("阿丽和小波谁买的相机更贵？"), "compare"
        )
        self.assertEqual(
            reasoning_question_kind("阿丽比小波高吗？"), "compare"
        )

    def test_transitive_kind(self) -> None:
        self.assertEqual(
            reasoning_question_kind("阿丽、小波、小王三个人里谁最高？"),
            "transitive",
        )
        self.assertEqual(
            reasoning_question_kind("阿丽比小波高，小波比小王高，谁最高？"),
            "transitive",
        )

    def test_plain_question_not_reasoning(self) -> None:
        self.assertIsNone(
            reasoning_question_kind("阿丽最喜欢的颜色是什么？")
        )
        self.assertIsNone(
            reasoning_question_kind("阿丽在2026年3月1日做了什么？")
        )


class PremisePackTests(unittest.TestCase):
    def test_transitive_chain_surfaces(self) -> None:
        engine = _reasoning_engine()
        results = engine.recall_reasoning(
            "阿丽、小波、小王三个人里谁最高？", top_k=8
        )
        contents = [r.item.content for r in results]
        self.assertIn("阿丽比小波高。", contents)
        self.assertIn("小波比小王高。", contents)

    def test_math_unit_price_premises_surface(self) -> None:
        engine = _reasoning_engine()
        results = engine.recall_reasoning(
            "阿丽和小波买的笔记本，谁的单价更贵？", top_k=8
        )
        contents = [r.item.content for r in results]
        self.assertIn("阿丽买了3本笔记本花了90元。", contents)
        self.assertIn("小波买了2本笔记本花了40元。", contents)

    def test_multi_entity_cities_surface(self) -> None:
        engine = _reasoning_engine()
        results = engine.recall_reasoning(
            "阿丽和小波最喜欢的城市分别是什么？", top_k=8
        )
        contents = [r.item.content for r in results]
        self.assertIn("阿丽最喜欢的城市是成都。", contents)
        self.assertIn("小波最喜欢的城市是杭州。", contents)

    def test_plain_recall_misses_distractor_dimension(self) -> None:
        engine = _reasoning_engine()
        plain = {r.item.content for r in engine.recall(
            "阿丽和小波买的笔记本，谁的单价更贵？", top_k=5
        )}
        packed = {r.item.content for r in engine.recall_reasoning(
            "阿丽和小波买的笔记本，谁的单价更贵？", top_k=8
        )}
        # the premise pack must add at least one premise plain recall missed
        self.assertTrue(
            packed - plain,
            msg="premise pack should surface additional same-dimension premises",
        )


if __name__ == "__main__":
    unittest.main()
