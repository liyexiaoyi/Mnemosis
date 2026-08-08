"""Tests for time-cell anchored temporal reasoning (round 25)."""

from __future__ import annotations

import unittest
from datetime import date, timedelta

from mnemosis import MemoryEngine
from mnemosis.temporal_reason import (
    anchor_dates,
    temporal_question_kind,
)
from mnemosis.types import MemoryKind, SourceRecord, SourceType, tokenize


def _engine_with_chain() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    start = date(2026, 3, 1)
    events = [
        ("alice bought camera on 2026-03-01.", "alice", "2026-03-01"),
        ("alice visited kyoto on 2026-03-02.", "alice", "2026-03-02"),
        ("alice had ramen for dinner on 2026-03-03.", "alice", "2026-03-03"),
        ("bob bought notebook on 2026-03-02.", "bob", "2026-03-02"),
    ]
    for content, person, iso in events:
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, iso],
            importance=0.5,
        )
    return engine


class TemporalMarkerTests(unittest.TestCase):
    def test_english_after(self) -> None:
        self.assertEqual(
            temporal_question_kind(
                "After Alice visiting Kyoto on 2026-02-03, "
                "what did Alice do next?"
            ),
            "after",
        )

    def test_english_before(self) -> None:
        self.assertEqual(
            temporal_question_kind("What did Alice do before 2026-03-02?"),
            "before",
        )

    def test_chinese_after(self) -> None:
        self.assertEqual(
            temporal_question_kind("阿丽在2026年3月1日买了相机之后，接下来做了什么？"),
            "after",
        )

    def test_chinese_before(self) -> None:
        self.assertEqual(
            temporal_question_kind("阿丽在2026年3月3日之前做了什么？"),
            "before",
        )

    def test_fact_query_not_temporal(self) -> None:
        self.assertIsNone(
            temporal_question_kind("请问阿丽最喜欢的颜色是什么？")
        )
        self.assertIsNone(
            temporal_question_kind("What is Alice's favorite color?")
        )

    def test_event_query_not_temporal(self) -> None:
        self.assertIsNone(
            temporal_question_kind("阿丽在2026年3月1日买了什么？")
        )
        self.assertIsNone(
            temporal_question_kind("What did Alice buy on 2026-03-01?")
        )

    def test_zh_date_normalized_to_iso(self) -> None:
        dates = anchor_dates(set(tokenize("阿丽在2026年3月1日买了相机。")))
        self.assertIn(date(2026, 3, 1), dates)


class TimeCellReasoningTests(unittest.TestCase):
    def test_after_returns_nearest_future_event(self) -> None:
        engine = _engine_with_chain()
        results = engine.recall(
            "After Alice bought camera on 2026-03-01, what did Alice do next?",
            top_k=5,
            temporal_reason=True,
        )
        contents = [r.item.content for r in results]
        self.assertIn("alice visited kyoto on 2026-03-02.", contents)
        # the nearest future event must be ranked before farther events
        self.assertLess(
            contents.index("alice visited kyoto on 2026-03-02."),
            contents.index("alice had ramen for dinner on 2026-03-03."),
        )

    def test_before_returns_nearest_past_event(self) -> None:
        engine = _engine_with_chain()
        results = engine.recall(
            "Before Alice had ramen for dinner on 2026-03-03, "
            "what did Alice do?",
            top_k=5,
            temporal_reason=True,
        )
        contents = [r.item.content for r in results]
        self.assertIn("alice visited kyoto on 2026-03-02.", contents)
        # the nearest-past event is the answer: it must rank first
        self.assertEqual(contents[0], "alice visited kyoto on 2026-03-02.")

    def test_transitive_two_hop(self) -> None:
        engine = _engine_with_chain()
        results = engine.recall(
            "Two events after Alice bought camera on 2026-03-01, "
            "what happened?",
            top_k=8,
            temporal_reason=True,
        )
        contents = [r.item.content for r in results]
        self.assertIn("alice had ramen for dinner on 2026-03-03.", contents)
        # transitive two-hop target outranks the anchor
        self.assertLess(
            contents.index("alice had ramen for dinner on 2026-03-03."),
            contents.index("alice bought camera on 2026-03-01."),
        )

    def test_cross_person_nearest_future_ranks_first(self) -> None:
        on = _engine_with_chain().recall(
            "After Alice bought camera on 2026-03-01, what did Bob do next?",
            top_k=5,
            temporal_reason=True,
        )
        off = _engine_with_chain().recall(
            "After Alice bought camera on 2026-03-01, what did Bob do next?",
            top_k=5,
            temporal_reason=False,
        )
        target = "bob bought notebook on 2026-03-02."
        self.assertEqual(on[0].item.content, target)
        self.assertNotEqual(off[0].item.content, target)

    def test_no_date_anchor_no_boost(self) -> None:
        engine = _engine_with_chain()
        before = {r.item.id for r in engine.recall(
            "What did Alice do after buying a camera?",
            top_k=5,
            temporal_reason=True,
        )}
        after = {r.item.id for r in engine.recall(
            "What did Alice do after buying a camera?",
            top_k=5,
            temporal_reason=False,
        )}
        self.assertEqual(before, after)

    def test_no_temporal_marker_no_boost(self) -> None:
        engine = _engine_with_chain()
        before = {r.item.id for r in engine.recall(
            "What did Alice buy on 2026-03-01?",
            top_k=5,
            temporal_reason=True,
        )}
        after = {r.item.id for r in engine.recall(
            "What did Alice buy on 2026-03-01?",
            top_k=5,
            temporal_reason=False,
        )}
        self.assertEqual(before, after)

    def test_other_person_not_boosted(self) -> None:
        on = _engine_with_chain().recall(
            "After Alice bought camera on 2026-03-01, what did Alice do next?",
            top_k=8,
            temporal_reason=True,
        )
        off = _engine_with_chain().recall(
            "After Alice bought camera on 2026-03-01, what did Alice do next?",
            top_k=8,
            temporal_reason=False,
        )
        bob_on = next(
            r for r in on if "bob bought notebook" in r.item.content
        )
        bob_off = next(
            r for r in off if "bob bought notebook" in r.item.content
        )
        # Bob's event may surface via token overlap, but the time-cell
        # mechanism must not touch it (score and reasons unchanged).
        self.assertAlmostEqual(bob_on.score, bob_off.score, places=6)
        self.assertFalse(
            any("\u65f6\u95f4\u7ec6\u80de" in reason for reason in bob_on.reasons)
        )


if __name__ == "__main__":
    unittest.main()
