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

    def test_due_items_prioritise_important_memories(self):
        """Rasch & Born (2013): rehearsal prioritises salient content."""
        curve = ForgettingCurve(decay_rate=0.05)
        scheduler = ReviewScheduler(curve, base_interval_hours=24)
        now = utcnow()
        low = make_item(
            content="low", created_at=now - timedelta(days=40),
            importance=0.3,
        )
        high = make_item(
            content="high", created_at=now - timedelta(days=20),
            importance=0.9,
        )
        mid = make_item(
            content="mid", created_at=now - timedelta(days=25),
            importance=0.6,
        )
        due = scheduler.due_items([low, high, mid], now=now, limit=2)
        self.assertEqual([i.content for i in due], ["high", "mid"])
        due2 = scheduler.due_items(
            [low, high, mid], now=now, limit=2, importance_first=False
        )
        self.assertEqual([i.content for i in due2], ["low", "mid"])

    def test_spacing_effect_durable_gain(self):
        """Cepeda et al. (2006): longer gap before a successful retrieval
        yields a larger durable (storage-strength) gain."""
        curve = ForgettingCurve(decay_rate=0.01)
        now = utcnow()
        recent = make_item(strength=0.5, created_at=now)
        spaced = make_item(strength=0.5, created_at=now - timedelta(days=5))
        recent.last_access_at = now
        spaced.last_access_at = now - timedelta(days=5)
        curve.reinforce_review(recent, delta=0.1, now=now, effort=0.5)
        curve.reinforce_review(spaced, delta=0.1, now=now, effort=0.5)
        self.assertGreater(
            spaced.storage_strength, recent.storage_strength
        )

    def test_effort_scaled_reinforcement(self):
        """Bjork & Kroll (2015): harder-but-successful retrieval reinforces
        more than an effortless one."""
        curve = ForgettingCurve(decay_rate=0.01)
        now = utcnow()
        easy = make_item(strength=0.5, created_at=now)
        hard = make_item(strength=0.5, created_at=now)
        easy.last_access_at = now
        hard.last_access_at = now
        curve.reinforce_review(easy, delta=0.1, now=now, effort=0.0)
        curve.reinforce_review(hard, delta=0.1, now=now, effort=1.0)
        self.assertGreater(hard.storage_strength, easy.storage_strength)

    def test_record_outcome_adaptive_spacing(self):
        """Smolen et al. (2016): failures reset the review streak so the next
        interval shrinks; successes extend it."""
        scheduler = ReviewScheduler(ForgettingCurve(), base_interval_hours=24)
        now = utcnow()
        item = make_item()
        scheduler.record_outcome(item, success=True, now=now)
        scheduler.record_outcome(item, success=True, now=now)
        self.assertEqual(item.review_streak, 2)
        self.assertEqual(item.retrieval_successes, 2)
        interval = (
            scheduler.next_review_at(item, now) - now
        ).total_seconds() / 3600.0
        self.assertAlmostEqual(interval, 48.0)  # base 24 * 2^1
        # failure resets
        scheduler.record_outcome(item, success=False, now=now)
        self.assertEqual(item.review_streak, 0)
        self.assertEqual(item.retrieval_failures, 1)
        next_at = scheduler.next_review_at(item, now)
        self.assertLessEqual(
            (next_at - now).total_seconds() / 3600.0, 24.0
        )


if __name__ == "__main__":
    unittest.main()
