import unittest
from datetime import timedelta

from mnemosis.forgetting import ForgettingCurve, ReviewScheduler
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType, utcnow


def make_item(**kwargs) -> MemoryItem:
    defaults = {
        "content": "a test memory",
        "kind": MemoryKind.EPISODIC,
        "source": SourceRecord(origin=SourceType.USER),
    }
    defaults.update(kwargs)
    return MemoryItem(**defaults)


class ForgettingCurveTest(unittest.TestCase):
    def test_decay_over_time(self):
        curve = ForgettingCurve(decay_rate=0.01)
        now = utcnow()
        old = make_item(created_at=now - timedelta(days=10))
        fresh = make_item(created_at=now)
        self.assertLess(curve.retrievability(old, now), curve.retrievability(fresh, now))
        self.assertLess(curve.retrievability(old, now), 1.0)

    def test_reinforce_restores_strength_and_marks_access(self):
        curve = ForgettingCurve(decay_rate=0.01)
        item = make_item(strength=0.5)
        curve.reinforce(item, delta=0.2)
        self.assertAlmostEqual(item.strength, 0.7)
        self.assertEqual(item.access_count, 1)
        self.assertIsNotNone(item.last_access_at)

    def test_is_forgotten_threshold(self):
        curve = ForgettingCurve(decay_rate=0.5)
        now = utcnow()
        item = make_item(created_at=now - timedelta(hours=10), strength=1.0)
        self.assertTrue(curve.is_forgotten(item, threshold=0.2, now=now))


class ReviewSchedulerTest(unittest.TestCase):
    def test_intervals_grow(self):
        scheduler = ReviewScheduler(ForgettingCurve(), base_interval_hours=24)
        self.assertAlmostEqual(scheduler.next_interval_hours(1), 24)
        self.assertAlmostEqual(scheduler.next_interval_hours(2), 48)
        self.assertAlmostEqual(scheduler.next_interval_hours(3), 96)

    def test_due_items_returns_decayed_first(self):
        curve = ForgettingCurve(decay_rate=0.05)
        scheduler = ReviewScheduler(curve, base_interval_hours=24)
        now = utcnow()
        old = make_item(created_at=now - timedelta(days=30), strength=1.0)
        fresh = make_item(created_at=now, strength=1.0)
        due = scheduler.due_items([fresh, old], now=now, limit=10, due_threshold=0.5)
        self.assertIn(old, due)
        self.assertNotIn(fresh, due)


if __name__ == "__main__":
    unittest.main()

