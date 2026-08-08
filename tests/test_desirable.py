"""Desirable-difficulty review scheduling (Bjork & Bjork 2011)."""

from __future__ import annotations

import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.forgetting import ForgettingCurve, ReviewScheduler
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType, utcnow


def _item(engine: MemoryEngine, strength: float, age_days: int) -> MemoryItem:
    return engine.remember(
        f"memory-{strength}-{age_days}",
        kind=MemoryKind.SEMANTIC,
        source=SourceRecord(origin=SourceType.USER),
        cues=[f"m{strength}"],
        strength=strength,
        created_at=utcnow() - timedelta(days=age_days),
    )


class DesirableDifficultyTests(unittest.TestCase):
    def test_due_items_prefer_moderate_difficulty(self) -> None:
        engine = MemoryEngine()
        # same importance; retrievability ~ strength * exp(-0.002*age*24)
        easy = _item(engine, 0.55, age_days=1)    # ~0.52 -> not due? 0.52 > 0.5
        moderate = _item(engine, 0.5, age_days=3)  # ~0.43
        hard = _item(engine, 0.5, age_days=30)     # ~0.12
        items = [easy, moderate, hard]
        now = utcnow()
        chosen = engine.review_due(
            limit=3, now=now, desirable_difficulty=True
        )
        self.assertEqual(chosen[0].id, moderate.id)
        plain = engine.review_due(limit=3, now=now)
        self.assertEqual(plain[0].id, hard.id)


if __name__ == "__main__":
    unittest.main()
