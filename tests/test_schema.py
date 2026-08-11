"""Tests for event-chain (schema) memory and temporal successor recall."""

import unittest

from mnemosis import MemoryEngine
from mnemosis.schema import EventChainIndex, _date_of
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class EventChainTest(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = MemoryEngine()
        self.user = SourceRecord(origin=SourceType.USER)

    def event(self, content: str, session: int) -> None:
        self.engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=self.user,
            cues=["alice", f"session{session}"],
            importance=0.5,
        )

    def test_chain_orders_events_and_links_successor(self) -> None:
        self.event("Alice visited the museum on 2026-02-01.", 1)
        self.event("Alice had ramen for dinner on 2026-02-02.", 1)
        self.event("Alice bought a camera on 2026-02-03.", 1)
        items = self.engine.backend.list(kind=MemoryKind.EPISODIC)
        by_date = sorted(items, key=lambda i: _date_of(i))
        chain = EventChainIndex(self.engine.backend)
        self.assertEqual(
            chain.next_event_id(by_date[0].id), by_date[1].id
        )
        self.assertEqual(
            chain.next_event_id(by_date[1].id), by_date[2].id
        )
        self.assertIsNone(chain.next_event_id(by_date[2].id))

    def test_temporal_successor_boost(self) -> None:
        self.event("Alice visited the aquarium on 2026-02-01.", 1)
        self.event("Alice had tacos for dinner on 2026-02-02.", 1)
        results = self.engine.recall(
            "After visiting the aquarium on 2026-02-01, what did Alice do next?",
            top_k=5,
        )
        contents = [r.item.content for r in results]
        self.assertIn("aquarium", contents[0])
        self.assertTrue(
            any("tacos" in c for c in contents),
            "temporal successor should surface via the event chain",
        )
        successor = next(
            r for r in results if "tacos" in r.item.content
        )
        self.assertTrue(
            any("\u65f6\u5e8f\u540e\u7ee7" in reason for reason in successor.reasons)
        )


if __name__ == "__main__":
    unittest.main()
