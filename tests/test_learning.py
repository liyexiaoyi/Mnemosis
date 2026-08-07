"""Tests for research-grounded learning mechanisms:
auto cue extraction, storage vs retrieval strength, testing effect,
reconsolidation updates, sleep prioritization, and the working set.
"""

import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.types import (
    MemoryKind,
    SourceRecord,
    SourceType,
    extract_cues,
    utcnow,
)


class LearningTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()
        self.user = SourceRecord(origin=SourceType.USER)

    def remember(self, content, **kwargs):
        kwargs.setdefault("kind", MemoryKind.SEMANTIC)
        kwargs.setdefault("source", self.user)
        return self.engine.remember(content, **kwargs)

    def test_extract_cues_from_content(self):
        cues = extract_cues("The SQLite locking fix went live today.")
        self.assertIn("sqlite", cues)
        self.assertIn("locking", cues)
        self.assertNotIn("the", cues)  # stopword
        self.assertNotIn("fix", cues)  # short latin word skipped

    def test_auto_cues_added_on_remember(self):
        item = self.remember("The SQLite locking issue was resolved.")
        self.assertIn("sqlite", item.cues)
        self.assertIn("locking", item.cues)

    def test_storage_strength_grows_slowly_and_durably(self):
        curve = self.engine.curve
        item = self.remember("A memory.", strength=0.5)
        self.assertEqual(item.storage_strength, 1.0)
        for _ in range(5):
            curve.reinforce(item, delta=0.1)
        self.assertAlmostEqual(item.strength, 1.0, places=6)
        self.assertAlmostEqual(item.storage_strength, 1.15)  # storage slow

        now = utcnow()
        low = self.remember(
            "A fact.",
            strength=0.5,
            storage_strength=1.0,
            created_at=now - timedelta(days=30),
        )
        high = self.remember(
            "Another fact.",
            strength=0.5,
            storage_strength=1.8,
            created_at=now - timedelta(days=30),
        )
        self.assertGreater(
            curve.retrievability(high, now), curve.retrievability(low, now)
        )

    def test_recall_reinforcement_scales_with_match(self):
        strong = self.remember(
            "alpha module design review",
            cues=["alpha"],
            strength=0.5,
        )
        weak = self.remember(
            "weather forecast today",
            cues=["beta"],
            strength=0.5,
        )
        self.engine.recall("alpha module design review", top_k=1)
        self.engine.recall("weather", top_k=1)
        self.assertGreater(strong.strength, weak.strength)

    def test_update_reconsolidation(self):
        item = self.remember(
            "The meeting is on Tuesday.",
            confidence=0.9,
        )
        confidence_before = item.confidence
        updated = self.engine.update(
            item.id, content="The meeting is on Wednesday."
        )
        self.assertEqual(updated.revision_count, 1)
        self.assertIsNotNone(updated.updated_at)
        self.assertLess(updated.confidence, confidence_before)
        results = self.engine.recall("meeting Wednesday", top_k=3)
        self.assertEqual(results[0].item.content, "The meeting is on Wednesday.")

    def test_update_rejects_semantic_duplicate(self):
        self.remember("Alpha fact one.")
        other = self.remember("Beta fact two.")
        with self.assertRaises(ValueError):
            self.engine.update(other.id, content="Alpha fact one.")

    def test_emotional_episode_promotes_earlier(self):
        now = utcnow()
        emotional = self.remember(
            "用户对截止日期感到非常焦虑。",
            kind=MemoryKind.EPISODIC,
            cues=["deadline"],
            affect="negative",
            created_at=now - timedelta(hours=12),
        )
        self.remember(
            "构建流水线的日常备注。",
            kind=MemoryKind.EPISODIC,
            created_at=now - timedelta(hours=12),
        )
        emotional.touch(now)
        report = self.engine.sleep(now=now)
        self.assertEqual(len(report.promoted), 1)
        self.assertEqual(report.promoted[0].content, emotional.content)

    def test_sleep_replays_recent_salient_episodes(self):
        """Gais et al. (2002): sleep replays recently encoded, salient traces,
        giving them a durable strength gain."""
        now = utcnow()
        recent = self.remember(
            "We shipped the new search index today.",
            kind=MemoryKind.EPISODIC,
            source=self.user,
            created_at=now - timedelta(hours=2),
            importance=0.8,
        )
        old = self.remember(
            "We shipped the old batch job a month ago.",
            kind=MemoryKind.EPISODIC,
            source=self.user,
            created_at=now - timedelta(days=40),
            importance=0.8,
        )
        storage_before = (recent.storage_strength, old.storage_strength)
        report = self.engine.sleep(now=now)
        self.assertGreaterEqual(report.replayed, 1)
        recent_after = self.engine.backend.get(recent.id)
        old_after = self.engine.backend.get(old.id)
        self.assertGreater(recent_after.storage_strength, storage_before[0])
        self.assertEqual(old_after.storage_strength, storage_before[1])

    def test_review_outcome_adaptive_spacing(self):
        """engine.review() drives the adaptive scheduler: success grows the
        streak and next interval; failure resets it (Smolen et al., 2016)."""
        from datetime import timedelta
        item = self.remember("A scheduled memory.")
        now = utcnow()
        storage_before = item.storage_strength
        ok = self.engine.review(item.id, success=True, now=now)
        self.assertEqual(ok.review_streak, 1)
        self.assertGreater(ok.storage_strength, storage_before)
        interval_after_success = (
            self.engine.scheduler.next_review_at(ok, now) - now
        ).total_seconds() / 3600.0
        self.assertAlmostEqual(interval_after_success, 24.0)
        failed = self.engine.review(item.id, success=False, now=now)
        self.assertEqual(failed.review_streak, 0)
        self.assertEqual(failed.retrieval_failures, 1)
        interval_after_failure = (
            self.engine.scheduler.next_review_at(failed, now) - now
        ).total_seconds() / 3600.0
        self.assertAlmostEqual(interval_after_failure, 24.0)

    def test_working_set_orders_by_recent_access(self):
        a = self.remember("Alpha.")
        b = self.remember("Beta.")
        self.remember("Gamma.")
        self.engine.recall("beta", top_k=1)
        self.engine.recall("alpha", top_k=1)
        working = self.engine.working_set(limit=2)
        self.assertEqual([w.id for w in working], [a.id, b.id])


if __name__ == "__main__":
    unittest.main()
