"""Gist vs verbatim retrieval preference (Fuzzy-Trace Theory; Brainerd & Reyna, 1990, 2002)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class FuzzyTraceTest(unittest.TestCase):
    def test_fact_question_prefers_semantic_gist(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "Alice prefers amber.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["alice", "amber"],
        )
        engine.remember(
            "Alice chose amber.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "amber"],
        )
        results = engine.recall(
            "What is Alice's favorite color?", top_k=2, kind_preference=True
        )
        self.assertEqual(
            results[0].item.content, "Alice prefers amber."
        )
        self.assertTrue(
            any("\u8981\u70b9" in reason for reason in results[0].reasons)
        )
        off = engine.recall(
            "What is Alice's favorite color?",
            top_k=2,
            kind_preference=False,
        )
        self.assertFalse(
            any("\u8981\u70b9" in reason for reason in off[0].reasons)
        )

    def test_event_question_prefers_episodic_verbatim(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "Alice bought coffee.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["alice", "coffee"],
        )
        engine.remember(
            "Alice bought coffee on 2026-03-01.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "coffee"],
        )
        results = engine.recall(
            "What did Alice buy on 2026-03-01?",
            top_k=2,
            kind_preference=True,
        )
        self.assertEqual(
            results[0].item.content,
            "Alice bought coffee on 2026-03-01.",
        )
        self.assertTrue(
            any("\u4e8b\u4ef6\u504f\u597d" in reason for reason in results[0].reasons)
        )

    def test_event_preference_requires_date_anchor(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "Alice bought coffee.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["alice", "coffee"],
        )
        # episodic without a date in cues/content must NOT get the boost
        engine.remember(
            "Alice bought coffee.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "coffee"],
        )
        results = engine.recall(
            "What did Alice buy on 2026-03-01?",
            top_k=2,
            kind_preference=True,
        )
        for r in results:
            self.assertFalse(
                any("\u4e8b\u4ef6\u504f\u597d" in reason for reason in r.reasons)
            )


if __name__ == "__main__":
    unittest.main()
