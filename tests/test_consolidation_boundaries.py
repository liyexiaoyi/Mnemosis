"""Protect distinct facts while preserving evidence-based accommodation."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, MemoryStatus, SourceRecord, SourceType

NOW = datetime(2026, 9, 26, tzinfo=timezone.utc)


class ConsolidationBoundaryTests(unittest.TestCase):
    def engine(self, disk):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        engine = MemoryEngine(str(Path(temp.name) / "memory.db") if disk else None,
                              auto_warmup=False)
        self.addCleanup(engine.close)
        return engine

    def fact(self, engine, content, *, evidence=1, cues=None, context=None,
             occurred_at=None, trust=1.0, confidence=0.9):
        return engine.remember(content, kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER, trust=trust,
                                occurred_at=occurred_at),
            cues=cues or ["alice"], evidence_count=evidence, context=context,
            confidence=confidence, created_at=NOW, auto_cues=False,
            auto_context=False)

    def assert_preserved(self, engine, items):
        for item in items:
            stored = engine.backend.get(item.id)
            self.assertEqual(stored.status, MemoryStatus.ACTIVE)
            self.assertAlmostEqual(stored.confidence, 0.9)
            self.assertIn(item.id, {r.item.id for r in engine.recall_bm25(
                item.content, top_k=10, kind=MemoryKind.SEMANTIC)})

    def test_shared_tag_does_not_retire_unrelated_fact(self):
        for disk in (False, True):
            for mode in ("sleep", "resolve_conflicts"):
                with self.subTest(disk=disk, mode=mode):
                    engine = self.engine(disk)
                    a = self.fact(engine, "Alice enjoys cycling.", evidence=9)
                    b = self.fact(engine, "Alice avoids peanuts.")
                    engine.recall_bm25("peanuts")  # exercise existing cache
                    self.assertEqual(engine.consolidator.detect_conflicts(), [])
                    for _ in range(3):
                        getattr(engine, mode)(now=NOW)
                    self.assert_preserved(engine, [a, b])

    def test_distinct_contexts_are_not_competing_claims(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                a = self.fact(engine, "The server port is 443.", evidence=9,
                              cues=["server"], context="production")
                b = self.fact(engine, "The server port is 8080.",
                              cues=["server"], context="development")
                self.assertEqual(engine.consolidator.detect_conflicts(), [])
                engine.sleep(now=NOW)
                engine.resolve_conflicts(now=NOW)
                self.assert_preserved(engine, [a, b])

    def test_distinct_event_times_preserve_historical_fact(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                a = self.fact(engine, "Alice lives in Paris.", evidence=9,
                              occurred_at=NOW - timedelta(days=90))
                b = self.fact(engine, "Alice lives in Berlin.", occurred_at=NOW)
                self.assertEqual(engine.consolidator.detect_conflicts(), [])
                engine.sleep(now=NOW)
                engine.resolve_conflicts(now=NOW)
                self.assert_preserved(engine, [a, b])

    def test_same_scope_conflict_still_accommodates(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                a = self.fact(engine, "The API rate limit is 500 per minute.",
                              cues=["api"], context="production", evidence=4,
                              occurred_at=NOW)
                b = self.fact(engine, "The API rate limit is 200 per minute.",
                              cues=["api"], context="production", occurred_at=NOW)
                self.assertEqual(len(engine.consolidator.detect_conflicts()), 1)
                engine.recall_bm25("rate limit", top_k=10)
                engine.sleep(now=NOW)
                self.assertNotIn(b.id, {r.item.id for r in engine.recall_bm25(
                    "rate limit", top_k=10)})
                self.assertEqual(engine.backend.get(a.id).status, MemoryStatus.ACTIVE)
                self.assertEqual(engine.backend.get(b.id).status, MemoryStatus.RECYCLED)

    def test_balanced_same_scope_keeps_both_and_flags_uncertainty(self):
        engine = self.engine(False)
        a = self.fact(engine, "Alice lives in Paris.")
        b = self.fact(engine, "Alice lives in Berlin.")
        engine.sleep(now=NOW)
        for item in [a, b]:
            stored = engine.backend.get(item.id)
            self.assertEqual(stored.status, MemoryStatus.ACTIVE)
            self.assertAlmostEqual(stored.confidence, 0.8)

    def test_low_trust_volume_cannot_retire_high_trust_fact(self):
        engine = self.engine(False)
        a = self.fact(engine, "Alice lives in Paris.", evidence=9, trust=0.2)
        b = self.fact(engine, "Alice lives in Berlin.", trust=1.0)
        engine.sleep(now=NOW)
        self.assertEqual(engine.backend.get(a.id).status, MemoryStatus.ACTIVE)
        self.assertEqual(engine.backend.get(b.id).status, MemoryStatus.ACTIVE)

    def test_candidate_detection_is_independent_of_cue_order(self):
        # The first cue removes all common tokens; the next cue does not.
        for cues in (["api limit", "service"], ["service", "api limit"]):
            with self.subTest(cues=cues):
                engine = self.engine(False)
                self.fact(engine, "The API limit is 200.", cues=cues)
                self.fact(engine, "The API limit is 500.", cues=cues)
                self.assertEqual(len(engine.consolidator.detect_conflicts()), 1)

    def test_recycled_candidate_cannot_retire_other_facts(self):
        engine = self.engine(False)
        a = self.fact(engine, "Alice likes tea.", evidence=9)
        b = self.fact(engine, "Alice likes coffee.", evidence=3)
        c = self.fact(engine, "Alice prefers cycling.")
        # Recycled snapshot entries must be ignored even when supplied by a caller.
        b.status = MemoryStatus.RECYCLED
        engine.backend.update(b)
        engine.consolidator._accommodation_phase(NOW, [a, b, c])
        self.assertEqual(engine.backend.get(c.id).status, MemoryStatus.ACTIVE)

    def test_equivalent_instants_remain_competing_claims(self):
        engine = self.engine(False)
        self.fact(engine, "Alice lives in Paris.", evidence=9, occurred_at=NOW)
        b = self.fact(engine, "Alice lives in Berlin.",
                      occurred_at=NOW.astimezone(timezone(timedelta(hours=8))))
        engine.resolve_conflicts(now=NOW)
        self.assertEqual(engine.backend.get(b.id).status, MemoryStatus.RECYCLED)

    def test_missing_scope_metadata_keeps_legacy_conflict_behavior(self):
        engine = self.engine(False)
        self.fact(engine, "Alice lives in Paris.", evidence=9,
                  context="profile", occurred_at=NOW)
        b = self.fact(engine, "Alice lives in Berlin.")
        engine.resolve_conflicts(now=NOW)
        self.assertEqual(engine.backend.get(b.id).status, MemoryStatus.RECYCLED)

    def test_retired_trace_cannot_count_as_another_accommodation(self):
        engine = self.engine(False)
        items = [self.fact(engine, f"Alice lives in city {n}.", evidence=count)
                 for n, count in enumerate([27, 9, 3])]
        self.assertEqual(engine.consolidator._accommodation_phase(NOW), 2)
        self.assertEqual(engine.backend.get(items[0].id).status, MemoryStatus.ACTIVE)

    def test_sqlite_reopen_preserves_scope_boundaries(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        path = str(Path(temp.name) / "memory.db")
        with MemoryEngine(path, auto_warmup=False) as engine:
            a = self.fact(engine, "Alice lives in Paris.", evidence=9,
                          occurred_at=NOW - timedelta(days=90))
            b = self.fact(engine, "Alice lives in Berlin.", occurred_at=NOW)
        with MemoryEngine(path, auto_warmup=False) as engine:
            engine.sleep(now=NOW)
            self.assert_preserved(engine, [a, b])


if __name__ == "__main__":
    unittest.main()
