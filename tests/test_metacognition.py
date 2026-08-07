import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.metacognition import ConfidenceLabel
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


class MetacognitionTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()

    def test_confidence_label_drops_with_decay(self):
        now = utcnow()
        fresh = self.engine.remember(
            "Fresh fact.",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            confidence=1.0,
        )
        label, value = self.engine.confidence(fresh, now)
        self.assertEqual(label, ConfidenceLabel.HIGH)
        self.assertGreaterEqual(value, 0.7)

        stale = self.engine.remember(
            "Old fact.",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            confidence=1.0,
            created_at=now - timedelta(days=60),
        )
        self.engine.curve.decay_rate = 0.05
        label, value = self.engine.confidence(stale, now)
        self.assertEqual(label, ConfidenceLabel.LOW)
        self.assertLess(value, 0.4)

    def test_should_confirm_low_confidence_inference(self):
        now = utcnow()
        inference = self.engine.remember(
            "Guessed fact.",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.INFERENCE),
            confidence=0.5,
            created_at=now - timedelta(days=30),
        )
        self.assertTrue(self.engine.meta.should_confirm(inference, now))

    def test_knowledge_gaps(self):
        self.engine.remember(
            "The user prefers Chinese.",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["user", "language"],
        )
        check = self.engine.check("sqlite debug session")
        self.assertIn("sqlite", check.gaps)
        self.assertIn("debug", check.gaps)

    def test_check_reports_items_and_contradictions(self):
        self.engine.remember(
            "Deadline is Friday.",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["deadline"],
            confidence=0.9,
        )
        self.engine.remember(
            "Deadline is Monday.",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["deadline"],
            confidence=0.9,
        )
        check = self.engine.check("what is the deadline?")
        self.assertTrue(check.items)
        self.assertEqual(len(check.contradictions), 1)


if __name__ == "__main__":
    unittest.main()

