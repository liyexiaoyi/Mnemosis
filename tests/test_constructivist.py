"""Constructivist schema assimilation/accommodation (Piaget; CAM, Li et al. 2025)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import (
    MemoryKind,
    MemoryStatus,
    SourceRecord,
    SourceType,
)


class ConstructivistMemoryTest(unittest.TestCase):
    def test_accommodation_retires_outdated_low_evidence_fact(self) -> None:
        engine = MemoryEngine()
        old = SourceRecord(origin=SourceType.USER, trust=0.8)
        new = SourceRecord(origin=SourceType.USER, trust=0.9)
        engine.remember(
            "The API rate limit is 200 per minute.",
            kind=MemoryKind.SEMANTIC,
            source=old,
            cues=["api"],
            evidence_count=1,
        )
        engine.remember(
            "The API rate limit is 500 per minute.",
            kind=MemoryKind.SEMANTIC,
            source=new,
            cues=["api"],
            evidence_count=4,
        )
        report = engine.sleep()
        self.assertGreaterEqual(report.accommodated, 1)
        items = {
            i.content: i for i in engine.backend.list_items(kind=MemoryKind.SEMANTIC)
        }
        self.assertIn("The API rate limit is 500 per minute.", items)
        self.assertNotIn("The API rate limit is 200 per minute.", items)
        results = engine.recall("api rate limit", top_k=3)
        self.assertEqual(
            results[0].item.content, "The API rate limit is 500 per minute."
        )

    def test_balanced_conflict_is_not_accommodated(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "The server is in Frankfurt.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["server"],
            evidence_count=1,
        )
        engine.remember(
            "The server is in Singapore.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["server"],
            evidence_count=1,
        )
        report = engine.sleep()
        self.assertEqual(report.accommodated, 0)
        active = [
            item
            for item in engine.backend.list_items(kind=MemoryKind.SEMANTIC)
            if item.status is MemoryStatus.ACTIVE
        ]
        self.assertEqual(len(active), 2)

    def test_assimilation_links_episode_to_existing_schema(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        schema = engine.remember(
            "Alice prefers dark mode.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["alice", "preference"],
        )
        episode = engine.remember(
            "Alice said she loves dark mode on Friday.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "preference"],
        )
        engine.sleep()
        self.assertGreater(
            engine.backend.link_weight(schema.id, episode.id), 0.0
        )
        related = engine.related(schema.id, depth=1)
        self.assertTrue(
            any(item.id == episode.id for item in related)
        )


if __name__ == "__main__":
    unittest.main()
