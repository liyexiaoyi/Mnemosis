"""Regression tests for retrieval learning boundaries and evidence lineage."""
from __future__ import annotations

import sqlite3
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


class LearningBoundaryTests(unittest.TestCase):
    def build(self, path=None):
        engine = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(engine.close)
        for text in ("Alice drinks green tea", "Alice buys green tea weekly", "Bob drinks black coffee"):
            engine.remember(text, kind=MemoryKind.EPISODIC,
                            source=SourceRecord(origin=SourceType.USER),
                            cues=["drinks", "preference"], strength=0.5)
        return engine

    def state(self, engine):
        return ([i.to_dict() for i in engine.store.all_active()], sorted(engine.backend.all_links()))

    def test_fused_recall_reinforces_only_final_result_once(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                directory = tempfile.TemporaryDirectory()
                self.addCleanup(directory.cleanup)
                tmp = directory.name
                engine = self.build(str(Path(tmp)/"memory.db") if disk else None)
                result = engine.recall_fused("Alice green tea", top_k=1, pass_k=10)
                self.assertEqual(len(result), 1)
                chosen = result[0].item.id
                for item in engine.store.all_active():
                    self.assertEqual(item.access_count, 1 if item.id == chosen else 0)

    def test_read_only_queries_leave_items_links_and_log_unchanged(self):
        engine = self.build()
        before = self.state(engine)
        log = engine.get_recall_log()
        for query in ("Alice green tea", "xyzunseen", "xyzunseen"):
            engine.recall(query, top_k=3, read_only=True)
            engine.recall_fused(query, top_k=2, read_only=True)
        self.assertEqual(self.state(engine), before)
        self.assertEqual(engine.get_recall_log(), log)

    def test_check_does_not_rehearse_or_link_candidates(self):
        engine = self.build()
        before = self.state(engine)
        for _ in range(3):
            check = engine.check("Alice green tea")
            self.assertTrue(check.items)
        self.assertEqual(self.state(engine), before)

    def test_diagnostic_trace_does_not_train_memory(self):
        engine = self.build()
        before = self.state(engine)
        for _ in range(3):
            self.assertTrue(engine.recall_trace("Alice green tea")["results"])
        self.assertEqual(self.state(engine), before)

    def test_fused_forwards_explicit_time_to_reinforcement(self):
        engine = self.build()
        now = utcnow() + timedelta(days=365)
        result = engine.recall_fused("Alice green tea", top_k=1, now=now)
        self.assertEqual(engine.backend.get(result[0].item.id).last_access_at, now)


class VerifiedFeedbackTests(unittest.TestCase):
    def engine(self, path=None):
        engine = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(engine.close)
        return engine

    def test_internal_retrieval_is_not_verified_success(self):
        engine = self.engine()
        item = engine.remember("Alice likes tea")
        for _ in range(100):
            engine.recall("Alice tea", top_k=1)
        fresh = engine.backend.get(item.id)
        self.assertEqual(getattr(fresh, "verified_successes", None), 0)
        self.assertIsNone(engine.verified_retrieval_confidence(fresh))

    def test_feedback_tracks_usefulness_without_asserting_truth(self):
        engine = self.engine()
        item = engine.remember("Alice likes tea", confidence=0.8)
        engine.record_feedback(item.id, useful=False)
        engine.record_feedback(item.id, useful=False)
        fresh = engine.backend.get(item.id)
        self.assertEqual(fresh.verified_failures, 2)
        self.assertEqual(fresh.verified_successes, 0)
        self.assertEqual(fresh.evidence_count, 1)
        self.assertEqual(fresh.confidence, 0.8)
        self.assertEqual(engine.verified_retrieval_confidence(fresh), 0.25)
        with self.assertRaises(ValueError):
            engine.record_feedback(item.id, useful="false")
        self.assertIsNone(engine.record_feedback("missing", useful=True))
        engine.forget(item.id)
        self.assertIsNone(engine.record_feedback(item.id, useful=True))

    def test_negative_feedback_never_strengthens_a_weak_memory(self):
        engine = self.engine()
        item = engine.remember("Alice tea", strength=0.05)
        result = engine.record_feedback(item.id, useful=False)
        self.assertLessEqual(result.strength, 0.05)

    def test_feedback_survives_reopen_and_export(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = str(Path(directory.name)/"memory.db")
        engine = self.engine(path)
        item = engine.remember("Alice likes tea")
        engine.record_feedback(item.id, useful=True)
        engine.record_feedback(item.id, useful=False)
        engine.close()
        reopened = self.engine(path)
        fresh = reopened.backend.get(item.id)
        self.assertEqual((fresh.verified_successes, fresh.verified_failures), (1, 1))
        other = self.engine()
        other.import_memories(reopened.export_memories())
        copy = other.backend.get(item.id)
        self.assertEqual((copy.verified_successes, copy.verified_failures), (1, 1))


class ConsolidationLineageTests(unittest.TestCase):
    def build(self, path=None):
        engine = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(engine.close)
        return engine

    def episode(self, engine, ref):
        item = engine.remember("Alice prefers green tea", kind=MemoryKind.EPISODIC,
            source=SourceRecord(origin=SourceType.USER, ref=ref), importance=0.9)
        item.created_at = utcnow() - timedelta(days=4)
        item.access_count = 3
        engine.backend.update(item)
        return item

    def test_repeated_sleep_does_not_inflate_evidence(self):
        engine = self.build()
        self.episode(engine, "conversation:1:turn:1")
        engine.sleep()
        first = engine.store.all_active(MemoryKind.SEMANTIC)[0].evidence_count
        for _ in range(9):
            engine.sleep()
        final = engine.store.all_active(MemoryKind.SEMANTIC)[0]
        self.assertEqual(final.evidence_count, first)
        self.assertEqual(len(final.evidence_sources), 1)

    def test_duplicate_source_and_new_source_are_distinguished(self):
        engine = self.build()
        self.episode(engine, "conversation:1:turn:1")
        engine.sleep()
        self.episode(engine, "conversation:1:turn:1")
        engine.sleep()
        self.assertEqual(engine.store.all_active(MemoryKind.SEMANTIC)[0].evidence_count, 1)
        self.episode(engine, "conversation:2:turn:1")
        engine.sleep()
        final = engine.store.all_active(MemoryKind.SEMANTIC)[0]
        self.assertEqual(final.evidence_count, 2)
        self.assertEqual(len(final.evidence_sources), 2)

    def test_lineage_survives_sqlite_reopen_and_batch_update(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = str(Path(directory.name)/"memory.db")
        engine = self.build(path)
        self.episode(engine, "conversation:1:turn:1")
        engine.sleep()
        first = engine.store.all_active(MemoryKind.SEMANTIC)[0]
        before = first.evidence_count
        engine.backend.update_many([first])
        engine.close()
        engine = self.build(path)
        engine.sleep()
        final = engine.store.all_active(MemoryKind.SEMANTIC)[0]
        self.assertEqual(final.evidence_count, before)
        self.assertEqual(len(final.evidence_sources), 1)


class MigrationAndClockTests(unittest.TestCase):
    build = ConsolidationLineageTests.build
    episode = ConsolidationLineageTests.episode

    def test_legacy_database_gains_empty_feedback_and_lineage(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = str(Path(directory.name)/"old.db")
        engine = self.build(path)
        episode = self.episode(engine, "old:turn:1")
        engine.sleep()
        semantic = engine.store.all_active(MemoryKind.SEMANTIC)[0]
        before = semantic.evidence_count
        engine.close()
        with sqlite3.connect(path) as db:
            for column in ("verified_successes", "verified_failures", "evidence_sources"):
                db.execute(f"ALTER TABLE memories DROP COLUMN {column}")
        db.close()
        engine = self.build(path)
        old = engine.backend.get(semantic.id)
        self.assertEqual((old.verified_successes, old.verified_failures), (0, 0))
        self.assertEqual(old.evidence_sources, {})
        engine.sleep()
        self.assertEqual(engine.backend.get(semantic.id).evidence_count, before)
        self.assertEqual(len(engine.backend.get(semantic.id).evidence_sources), 1)
        portable = self.build()
        portable.import_memories(engine.export_memories())
        portable.sleep()
        self.assertEqual(portable.backend.get(semantic.id).evidence_count, before)

    def test_revision_does_not_inherit_old_fact_evidence_or_feedback(self):
        engine = self.build()
        self.episode(engine, "a")
        self.episode(engine, "b")
        engine.sleep()
        episode = engine.store.all_active(MemoryKind.EPISODIC)[0]
        engine.record_feedback(episode.id, useful=True)
        engine.update(episode.id, content="Alice prefers coffee now")
        engine.sleep()
        updated = engine.backend.get(episode.id)
        self.assertEqual(updated.evidence_count, 1)
        self.assertEqual(updated.verified_successes, 0)
        semantic = next(i for i in engine.store.all_active(MemoryKind.SEMANTIC)
                        if i.content == "Alice prefers coffee now")
        self.assertEqual(semantic.evidence_count, 1)
        self.assertEqual(len(semantic.evidence_sources), 1)

    def test_explicit_clock_is_independent_of_previous_engine(self):
        future = datetime(2040, 1, 1, tzinfo=timezone.utc)
        past = datetime(2030, 1, 1, tzinfo=timezone.utc)
        first = self.build()
        a = first.remember("Alice tea")
        first.record_feedback(a.id, useful=True, now=future)
        second = self.build()
        b = second.remember("Bob coffee")
        second.record_feedback(b.id, useful=True, now=past)
        self.assertEqual(second.backend.get(b.id).last_access_at, past)


class BackgroundAndProbeTests(unittest.TestCase):
    build = ConsolidationLineageTests.build

    def test_delayed_reinforcement_preserves_new_feedback_and_revision(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        engine = self.build(str(Path(directory.name)/"memory.db"))
        item = engine.remember("Alice tea")
        stale = engine.backend.get(item.id)
        stale.retrieval_successes += 1
        engine.record_feedback(item.id, useful=False)
        engine.store.enqueue_reinforce([stale])
        engine.store._reinforce_queue.join()
        self.assertEqual(engine.backend.get(item.id).verified_failures, 1)
        stale = engine.backend.get(item.id)
        engine.update(item.id, content="Alice coffee now")
        engine.store.enqueue_reinforce([stale])
        engine.store._reinforce_queue.join()
        self.assertEqual(engine.backend.get(item.id).content, "Alice coffee now")

    def test_fixed_time_fallback_probe_does_not_reuse_old_ranking_score(self):
        engine = self.build()
        start = datetime(2030, 1, 1, tzinfo=timezone.utc)
        item = engine.remember("Alice tea", auto_cues=False)
        item.created_at = start
        engine.backend.update(item)
        first = engine.recall("zzzxunknown", read_only=True, now=start)
        later = engine.recall("zzzxunknown", read_only=True, now=start + timedelta(days=90))
        self.assertTrue(first and later)
        self.assertLess(later[0].score, first[0].score)


class FinalReviewTests(unittest.TestCase):
    build = ConsolidationLineageTests.build
    episode = ConsolidationLineageTests.episode

    def test_legacy_migration_counts_new_source_at_first_sleep(self):
        engine = self.build()
        self.episode(engine, "old")
        engine.sleep()
        semantic = engine.store.all_active(MemoryKind.SEMANTIC)[0]
        semantic.evidence_sources = {}
        engine.backend.update(semantic)
        old = engine.store.all_active(MemoryKind.EPISODIC)[0]
        old.evidence_sources = {}
        engine.backend.update(old)
        self.episode(engine, "new")
        engine.sleep()
        final = engine.backend.get(semantic.id)
        self.assertEqual(final.evidence_count, 2)
        self.assertEqual(sum(final.evidence_sources.values()), 2)

    def test_dense_pass_respects_kind_and_directed_forgetting(self):
        from mnemosis.embedding import NGramEmbedder
        class Index:
            def __init__(self, ids):
                self.ids = ids
            def search(self, vector, top_k):
                return [(ident, 1.0) for ident in self.ids[:top_k]]
        for indexed in (True, False):
            with self.subTest(indexed=indexed):
                engine = self.build()
                hidden = engine.remember("Alice likes tea", kind=MemoryKind.SEMANTIC)
                episode = engine.remember("Alice drinks tea", kind=MemoryKind.EPISODIC)
                engine.suppress_memories([hidden.id])
                results = engine.recall_fused("Alice tea", kind=MemoryKind.SEMANTIC,
                    read_only=True, dense_embedder=NGramEmbedder(),
                    vector_index=Index([episode.id, hidden.id]) if indexed else None)
                self.assertEqual(results, [])


    def test_dense_override_does_not_query_another_embedders_index(self):
        from mnemosis.embedding import NGramEmbedder
        class Index:
            calls = 0
            def search(self, vector, top_k):
                self.calls += 1
                return []
        engine = self.build()
        engine.remember("Alice tea")
        engine.vector_index = Index()
        engine.index_embedder = NGramEmbedder()
        engine.recall_fused("Alice tea", read_only=True, dense_embedder=NGramEmbedder())
        self.assertEqual(engine.vector_index.calls, 0)


if __name__ == "__main__":
    unittest.main()
