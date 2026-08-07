"""Hippocampal pattern separation (Bakker et al., 2008, Science)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _build() -> MemoryEngine:
    user = SourceRecord(origin=SourceType.USER)
    engine = MemoryEngine()
    engine.remember(
        "Alice visited the aquarium on 2026-03-01.",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["alice", "2026-03-01", "session0"],
        auto_cues=False,
    )
    # near-duplicate: same date/place, different person.
    engine.remember(
        "Bob visited the aquarium on 2026-03-01.",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["bob", "2026-03-01", "session0"],
        auto_cues=False,
    )
    # shares two cues with A but different content (low lexical overlap).
    engine.remember(
        "Alice bought coffee beans on 2026-03-02.",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["alice", "2026-03-02", "session0"],
        auto_cues=False,
    )
    return engine


class PatternSeparationTest(unittest.TestCase):
    def test_near_duplicate_is_penalized_and_separated(self) -> None:
        engine = _build()
        with_sep = engine.recall("Alice aquarium 2026-03-01", top_k=5)
        self.assertEqual(
            with_sep[0].item.content,
            "Alice visited the aquarium on 2026-03-01.",
        )
        bob_on = next(
            r for r in with_sep
            if r.item.content == "Bob visited the aquarium on 2026-03-01."
        )
        self.assertTrue(
            any("模式分离" in reason for reason in bob_on.reasons)
        )

        engine_off = _build()
        off = engine_off.recall(
            "Alice aquarium 2026-03-01", top_k=5, separation=False
        )
        bob_off = next(
            r for r in off
            if r.item.content == "Bob visited the aquarium on 2026-03-01."
        )
        self.assertGreater(bob_off.score, bob_on.score)
        # the winner must stay on top in both modes
        self.assertEqual(
            off[0].item.content,
            "Alice visited the aquarium on 2026-03-01.",
        )

    def test_low_overlap_shared_cue_item_is_not_penalized(self) -> None:
        engine = _build()
        results = engine.recall("Alice aquarium", top_k=5)
        coffee = next(
            r for r in results
            if r.item.content == "Alice bought coffee beans on 2026-03-02."
        )
        self.assertFalse(
            any("模式分离" in reason for reason in coffee.reasons)
        )


if __name__ == "__main__":
    unittest.main()
