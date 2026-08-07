"""Hippocampal pattern completion (Rolls, 2013; Theves et al., 2024).

A partial cue should be able to re-activate a whole well-integrated pattern:
when the query overlaps only part of a memory, strongly linked neighbours
(strong link weight + at least two shared cues) of that partial match receive
a bounded completion boost, so weakly retrievable members of the same
pattern can resurface.
"""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _build() -> MemoryEngine:
    user = SourceRecord(origin=SourceType.USER)
    engine = MemoryEngine()
    # A: well-known anchor pattern.
    engine.remember(
        "Alice visited the aquarium on 2026-03-01.",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["alice", "2026-03-01", "session0"],
        importance=0.5,
        auto_cues=False,
    )
    # B: strongly linked to A (shares two cues), weak on its own.
    engine.remember(
        "Alice bought a notebook during session0.",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["alice", "session0"],
        importance=0.3,
        auto_cues=False,
    )
    # C: linked to A but shares only one cue (different pattern).
    engine.remember(
        "Bob visited the museum on 2026-03-01.",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["bob", "2026-03-01"],
        importance=0.8,
        auto_cues=False,
    )
    # D: not linked to A at all.
    engine.remember(
        "Dana likes painting.",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["dana"],
        importance=0.7,
        auto_cues=False,
    )
    return engine


class PatternCompletionTest(unittest.TestCase):
    def test_mechanism_boosts_only_strongly_linked_two_cue_neighbors(self) -> None:
        engine = _build()
        items = {i.content: i for i in engine.backend.list()}
        a = items["Alice visited the aquarium on 2026-03-01."]
        b = items["Alice bought a notebook during session0."]
        c = items["Bob visited the museum on 2026-03-01."]
        d = items["Dana likes painting."]
        scored = [
            (0.6, 0.6, a, ["overlap"], True),
            (0.2, 0.0, b, [], False),
            (0.25, 0.0, c, [], False),
            (0.3, 0.0, d, [], False),
        ]
        engine.store._pattern_completion(
            scored,
            min_overlap=0.25,
            max_overlap=0.95,
            link_weight_min=0.8,
            min_shared_cues=2,
            boost_scale=0.9,
            max_roots=4,
            max_neighbors=8,
            max_appended=16,
        )
        by_id = {entry[2].id: entry for entry in scored}
        self.assertAlmostEqual(by_id[b.id][0], 0.6 * 0.9, places=3)
        self.assertEqual(by_id[c.id][0], 0.25)
        self.assertEqual(by_id[d.id][0], 0.3)
        self.assertEqual(engine.store.pattern_completions, 1)

    def test_full_match_is_not_a_partial_cue(self) -> None:
        engine = _build()
        items = {i.content: i for i in engine.backend.list()}
        a = items["Alice visited the aquarium on 2026-03-01."]
        b = items["Alice bought a notebook during session0."]
        scored = [
            (0.9, 1.0, a, ["overlap"], True),
            (0.2, 0.0, b, [], False),
        ]
        engine.store._pattern_completion(
            scored,
            min_overlap=0.25,
            max_overlap=0.95,
            link_weight_min=0.8,
            min_shared_cues=2,
            boost_scale=0.8,
            max_roots=4,
            max_neighbors=8,
            max_appended=16,
        )
        self.assertEqual(engine.store.pattern_completions, 0)

    def test_recall_stays_deterministic_with_completion(self) -> None:
        engine = _build()
        first = engine.recall("Alice aquarium trip 2026-03-01", top_k=3)
        second = engine.recall("Alice aquarium trip 2026-03-01", top_k=3)
        self.assertEqual(
            [r.item.content for r in first],
            [r.item.content for r in second],
        )
        self.assertEqual(
            first[0].item.content,
            "Alice visited the aquarium on 2026-03-01.",
        )


if __name__ == "__main__":
    unittest.main()
