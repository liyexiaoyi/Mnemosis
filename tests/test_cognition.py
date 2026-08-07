"""Tests for research-grounded mechanisms:
context-dependence, emotional persistence, evidence accumulation,
retrieval-induced forgetting, and blocking detection.
"""

import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


class CognitionTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()
        self.user = SourceRecord(origin=SourceType.USER)

    def remember(self, content, **kwargs):
        kwargs.setdefault("kind", MemoryKind.SEMANTIC)
        kwargs.setdefault("source", self.user)
        return self.engine.remember(content, **kwargs)

    def test_context_dependent_recall_boost(self):
        a = self.remember(
            "We reviewed the alpha module design.",
            kind=MemoryKind.EPISODIC,
            context="project-a",
            cues=["alpha"],
        )
        self.remember(
            "We reviewed the alpha module design.",
            kind=MemoryKind.EPISODIC,
            context="project-b",
            cues=["alpha"],
        )
        results = self.engine.recall(
            "alpha module design", context="project-a", top_k=5
        )
        self.assertEqual(results[0].item.id, a.id)
        score_a = next(r.score for r in results if r.item.id == a.id)
        score_b = next(r.score for r in results if r.item.id != a.id)
        self.assertGreater(score_a, score_b)
        self.assertIn("context match", results[0].reasons)

    def test_emotional_memory_decays_slower(self):
        now = utcnow()
        self.engine.curve.decay_rate = 0.01
        neutral = self.remember(
            "A routine note about the build pipeline.",
            created_at=now - timedelta(days=10),
        )
        emotional = self.remember(
            "The user was very anxious about the deadline.",
            affect="negative",
            created_at=now - timedelta(days=10),
        )
        neutral_r = self.engine.curve.retrievability(neutral, now)
        emotional_r = self.engine.curve.retrievability(emotional, now)
        self.assertGreater(emotional_r, neutral_r)
        self.assertEqual(emotional.affect, "negative")

    def test_invalid_affect_is_rejected(self):
        item = self.remember("A note.", affect="not-a-real-affect")
        self.assertIsNone(item.affect)

    def test_evidence_accumulation_during_sleep(self):
        now = utcnow()
        content = "We fixed the SQLite bug."
        for _ in range(2):
            self.remember(
                content,
                kind=MemoryKind.EPISODIC,
                cues=["sqlite", "fix"],
                created_at=now - timedelta(days=2),
            )
        for _ in range(3):
            self.engine.recall("sqlite fix", top_k=5)
        report = self.engine.sleep(now=now)
        # near-duplicate episodes are merged first (complementary learning
        # systems), so the repeated evidence promotes as a single trace.
        self.assertEqual(report.merged, 1)
        self.assertEqual(len(report.promoted), 1)
        semantic = self.engine.store.all_active(MemoryKind.SEMANTIC)[0]
        self.assertEqual(semantic.evidence_count, 2)
        self.assertGreaterEqual(semantic.confidence, 0.7)

    def test_retrieval_induced_forgetting(self):
        target = self.remember(
            "The user likes coffee.",
            cues=["coffee", "user"],
        )
        rival = self.remember(
            "The user likes tea.",
            cues=["coffee", "user"],
        )
        strength_before = rival.strength
        results = self.engine.recall("coffee", top_k=1, suppression_factor=0.05)
        self.assertEqual(results[0].item.id, target.id)
        refreshed = self.engine.backend.get(rival.id)
        self.assertLess(refreshed.strength, strength_before)
        self.assertAlmostEqual(refreshed.strength, strength_before - 0.05)

    def test_blocked_retrieval_detection(self):
        blocked = self.remember(
            "An unrelated topic paragraph.",
            cues=["alpha"],
            confidence=0.9,
        )
        self.remember(
            "alpha details are here",
            cues=["beta"],
            confidence=0.9,
        )
        check = self.engine.check("alpha details", top_k=1)
        self.assertTrue(any(item.id == blocked.id for item in check.blocked))

    def test_associative_expansion_surfaces_linked_neighbor(self):
        first = self.engine.remember(
            "Alice visited the aquarium on 2026-02-02.",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["alice", "2026-02-02", "session0"],
        )
        second = self.engine.remember(
            "Alice bought a camera on 2026-02-03.",
            kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["alice", "2026-02-03", "session0"],
        )
        results = self.engine.recall(
            "after visiting the aquarium, what did Alice do next?", top_k=5
        )
        contents = [r.item.content for r in results]
        self.assertIn(first.content, contents)
        self.assertIn(second.content, contents)
        self.assertTrue(
            any("linked to" in reason for r in results for reason in r.reasons)
        )

    def test_reinforcement_does_not_dominate_exact_match(self):
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        target = engine.remember(
            "Alice bought a vinyl record on 2026-07-08.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["alice", "2026-07-08", "session26"],
        )
        filler = engine.remember(
            "Alice's favorite color is coral.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["alice", "color"],
        )
        for _ in range(20):
            engine.recall("alice favorite color", top_k=1)
        self.assertGreater(
            engine.curve.retrievability(filler), 1.0  # storage multiplier
        )
        results = engine.recall(
            "What did Alice buy on 2026-07-08?", top_k=3
        )
        self.assertEqual(results[0].item.id, target.id)


if __name__ == "__main__":
    unittest.main()
