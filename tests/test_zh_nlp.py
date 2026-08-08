"""Chinese synonym expansion (round 31, 中文专项优化)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType
from mnemosis.zh_nlp import expand_synonyms, has_cjk


class SynonymExpansionTests(unittest.TestCase):
    def test_has_cjk(self) -> None:
        self.assertTrue(has_cjk("怎么筹备去旅游"))
        self.assertFalse(has_cjk("how to prepare"))

    def test_expand_travel_group(self) -> None:
        terms = expand_synonyms({"筹备", "旅游"})
        self.assertTrue({"准备", "旅行"} <= terms)

    def test_expand_move_group(self) -> None:
        terms = expand_synonyms({"迁居"})
        self.assertIn("搬家", terms)

    def test_non_chinese_untouched(self) -> None:
        terms = expand_synonyms({"travel", "prepare"})
        self.assertEqual(terms, {"travel", "prepare"})


class SynonymRecallTests(unittest.TestCase):
    def test_synonym_question_finds_memory(self) -> None:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "阿丽在2026年4月3日准备了去旅行的行李。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["阿丽", "2026-04-03"],
        )
        results = engine.recall("阿丽是怎么筹备去旅游的？", top_k=3)
        self.assertEqual(
            results[0].item.content,
            "阿丽在2026年4月3日准备了去旅行的行李。",
        )

    def test_move_synonym(self) -> None:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "琳琳在2026年6月1日找了搬家公司。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["琳琳", "2026-06-01"],
        )
        results = engine.recall("琳琳是怎么迁居的？", top_k=3)
        self.assertEqual(
            results[0].item.content,
            "琳琳在2026年6月1日找了搬家公司。",
        )

    def test_hotel_synonym(self) -> None:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "小波在2026年5月2日订了宾馆。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["小波", "2026-05-02"],
        )
        results = engine.recall("小波订的酒店叫什么？", top_k=3)
        self.assertEqual(
            results[0].item.content,
            "小波在2026年5月2日订了宾馆。",
        )



if __name__ == "__main__":
    unittest.main()
