"""Amygdala-modulated emotional consolidation (McGaugh, 2004; Krenz et al., 2025)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class EmotionalConsolidationTest(unittest.TestCase):
    def test_recurring_emotional_episodes_consolidate_stronger_than_neutral(
        self,
    ) -> None:
        user = SourceRecord(origin=SourceType.USER)
        engine = MemoryEngine()
        for _ in range(2):
            engine.remember(
                "Alice felt anxious before the big launch.",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=["alice", "launch"],
                importance=0.6,
                confidence=0.8,
                strength=0.8,
                affect="negative",
            )
        for _ in range(2):
            engine.remember(
                "Alice reviewed the release notes.",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=["alice", "launch"],
                importance=0.6,
                confidence=0.8,
                strength=0.8,
            )
        report = engine.sleep()
        self.assertGreater(report.emotion_boosted, 0)

        emotional = next(
            item
            for item in engine.backend.list()
            if item.affect == "negative"
        )
        neutral = next(
            item
            for item in engine.backend.list()
            if item.affect is None
            and "release notes" in item.content
        )
        self.assertGreater(emotional.confidence, neutral.confidence)
        self.assertGreater(emotional.storage_strength, neutral.storage_strength)
        self.assertGreater(emotional.strength, neutral.strength)

    def test_emotional_links_are_stronger_than_neutral(self) -> None:
        user = SourceRecord(origin=SourceType.USER)
        engine = MemoryEngine()
        engine.remember(
            "Alice felt anxious before the launch.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "launch"],
            affect="negative",
        )
        engine.remember(
            "Alice felt relieved after the launch.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "launch"],
            affect="positive",
        )
        engine.remember(
            "Bob checked the schedule on Tuesday.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["bob", "schedule"],
        )
        engine.remember(
            "Carol updated the tracker on Wednesday.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["carol", "tracker"],
        )
        engine.sleep()
        by_content = {item.content: item for item in engine.backend.list()}
        emo_a = by_content["Alice felt anxious before the launch."]
        emo_b = by_content["Alice felt relieved after the launch."]
        neu_a = by_content["Bob checked the schedule on Tuesday."]
        neu_b = by_content["Carol updated the tracker on Wednesday."]
        self.assertEqual(
            engine.backend.link_weight(emo_a.id, emo_b.id), 1.2
        )
        # neutral pair shares no cues -> never linked.
        self.assertEqual(engine.backend.link_weight(neu_a.id, neu_b.id), 0.0)

    def test_emotional_promotion_gets_confidence_bonus(self) -> None:
        from datetime import timedelta

        from mnemosis.types import utcnow

        user = SourceRecord(origin=SourceType.USER)
        engine = MemoryEngine()
        now = utcnow()
        item = engine.remember(
            "Alice was thrilled about the new office.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "office"],
            importance=0.7,
            affect="positive",
            created_at=now - timedelta(days=2),
        )
        for _ in range(2):
            engine.recall("new office", top_k=1)  # access_count grows
        engine.sleep(now=now)
        semantic = [
            item
            for item in engine.backend.list(kind=MemoryKind.SEMANTIC)
            if "new office" in item.content
        ]
        self.assertTrue(semantic)
        self.assertGreaterEqual(semantic[0].confidence, 0.65)


if __name__ == "__main__":
    unittest.main()
