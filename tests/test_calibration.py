"""Metacognitive confidence calibration (Lichtenstein et al., 1977)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.metacognition import ConfidenceLabel
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class CalibrationTest(unittest.TestCase):
    def test_failure_history_lowers_confidence(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "The server is in Frankfurt.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["server"],
        )
        item.retrieval_successes = 1
        item.retrieval_failures = 9
        engine.backend.update(item)
        raw = engine.confidence(item)[1]
        label, calibrated = engine.calibrated_confidence(item)
        self.assertLess(calibrated, raw)
        self.assertIsNot(label, ConfidenceLabel.HIGH)

    def test_success_history_raises_low_confidence(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "The server is in Frankfurt.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["server"],
            confidence=0.3,
        )
        item.retrieval_successes = 9
        item.retrieval_failures = 1
        engine.backend.update(item)
        raw = engine.confidence(item)[1]
        calibrated = engine.calibrated_confidence(item)[1]
        self.assertGreater(calibrated, raw)

    def test_insufficient_evidence_keeps_heuristic(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "The server is in Frankfurt.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["server"],
        )
        self.assertIsNone(engine.meta.calibrate(item))
        raw = engine.confidence(item)
        self.assertEqual(
            engine.calibrated_confidence(item), raw
        )

    def test_calibration_reduces_ece_on_overconfident_set(self) -> None:
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for i in range(20):
            item = engine.remember(
                f"fact {i} is true.",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"cue{i}"],
                confidence=0.95,
            )
            item.retrieval_successes = 1
            item.retrieval_failures = 9  # empirical ~0.17 vs predicted 0.95
            engine.backend.update(item)
        items = engine.backend.list()
        raw_stats = engine.meta.calibration_stats(items)
        self.assertGreater(raw_stats["ece"], 0.3)
        # calibrated predictions should be closer to the empirical rate
        ece_sum = 0.0
        n = 0
        for item in items:
            pred = engine.meta.calibrated_confidence(item)[1]
            emp = engine.meta.calibrate(item)
            ece_sum += abs(pred - emp)
            n += 1
        self.assertLess(ece_sum / n, raw_stats["ece"])


if __name__ == "__main__":
    unittest.main()
