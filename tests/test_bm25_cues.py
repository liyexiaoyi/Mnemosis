"""BM25 candidate and bounded fusion contracts (real storage backends)."""
import math
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class BM25CueTests(unittest.TestCase):
    def engine(self, disk=False):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = str(Path(directory.name)/"memory.db") if disk else None
        engine = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(engine.close)
        return engine, path

    def remember(self, engine, text, kind=MemoryKind.EPISODIC):
        return engine.remember(text, kind=kind, cues=[], auto_cues=False, auto_context=False,
                               source=SourceRecord(origin=SourceType.USER))

    def test_matches_reference_formula_and_returns_no_zero_match(self):
        engine, _ = self.engine()
        a = self.remember(engine, "tea tea coffee")
        b = self.remember(engine, "tea")
        self.remember(engine, "coffee cake")
        results = engine.recall_bm25("tea", top_k=10)
        self.assertEqual([r.item.id for r in results], [b.id, a.id])
        idf = math.log(1 + (3 - 2 + 0.5)/(2 + 0.5))
        self.assertAlmostEqual(results[0].score, idf * 2.5/(1+1.5*(0.25+0.75*1/2)))
        self.assertEqual(engine.recall_bm25("zzzxunknown"), [])
        self.assertEqual(engine.recall_bm25("tea", top_k=0), [])

    def test_filters_before_top_k_and_queries_are_read_only(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine, _ = self.engine(disk)
                hidden = self.remember(engine, "tea", MemoryKind.SEMANTIC)
                excluded = self.remember(engine, "tea tea", MemoryKind.SEMANTIC)
                wanted = self.remember(engine, "tea coffee", MemoryKind.SEMANTIC)
                self.remember(engine, "tea", MemoryKind.EPISODIC)
                engine.suppress_memories([hidden.id])
                before = [i.to_dict() for i in engine.store.all_active()]
                links = engine.backend.all_links()
                for _ in range(2):
                    results = engine.recall_bm25("tea", top_k=1, kind=MemoryKind.SEMANTIC,
                                                 exclude_ids={excluded.id})
                    self.assertEqual([r.item.id for r in results], [wanted.id])
                self.assertEqual([i.to_dict() for i in engine.store.all_active()], before)
                self.assertEqual(engine.backend.all_links(), links)

    def test_cache_tracks_update_forget_restore_import_and_reopen(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine, path = self.engine(disk)
                item = self.remember(engine, "tea")
                self.assertTrue(engine.recall_bm25("tea"))
                engine.update(item.id, content="coffee")
                self.assertFalse(engine.recall_bm25("tea"))
                self.assertTrue(engine.recall_bm25("coffee"))
                engine.forget(item.id)
                self.assertFalse(engine.recall_bm25("coffee"))
                engine.restore(item.id)
                self.assertTrue(engine.recall_bm25("coffee"))
                donor, _ = self.engine()
                other = self.remember(donor, "mango")
                engine.import_memories(donor.export_memories())
                self.assertEqual(engine.recall_bm25("mango")[0].item.id, other.id)
                if disk:
                    engine.close()
                    reopened = MemoryEngine(path, auto_warmup=False)
                    self.addCleanup(reopened.close)
                    self.assertEqual(reopened.recall_bm25("coffee")[0].item.id, item.id)

    def test_sqlite_cache_detects_other_connection_writes(self):
        first, path = self.engine(True)
        item = self.remember(first, "tea")
        self.assertTrue(first.recall_bm25("tea"))
        # Existing single-write ingestion batches term commits; release that
        # write transaction before simulating a separately committed writer.
        first.backend._conn.commit()
        import sqlite3
        from mnemosis.types import hash_content
        connection = sqlite3.connect(path)
        try:
            with connection:
                connection.execute("UPDATE memories SET content=?, content_hash=? WHERE id=?",
                                   ("coffee", hash_content("coffee"), item.id))
        finally:
            connection.close()
        self.assertFalse(first.recall_bm25("tea"))
        self.assertTrue(first.recall_bm25("coffee"))

    def test_bounded_fusion_is_weight_scale_invariant_and_reinforces_once(self):
        engine, _ = self.engine()
        a = self.remember(engine, "Alice tea")
        b = self.remember(engine, "Alice coffee")
        fixed = datetime(2030, 1, 1, tzinfo=timezone.utc)
        kwargs = dict(kw_weight=0, ng_weight=0, normalize_fusion=True, now=fixed, top_k=1)
        small = engine.recall_fused("Alice tea", bm25_weight=1, read_only=True, **kwargs)
        large = engine.recall_fused("Alice tea", bm25_weight=10, read_only=True, **kwargs)
        self.assertEqual([r.item.id for r in small], [a.id])
        self.assertAlmostEqual(small[0].score, large[0].score)
        self.assertLessEqual(small[0].score, 1.25)
        engine.recall_fused("Alice tea", bm25_weight=1, **kwargs)
        self.assertEqual(engine.backend.get(a.id).access_count, 1)
        self.assertEqual(engine.backend.get(b.id).access_count, 0)

    def test_warm_query_does_not_retokenize_the_corpus(self):
        from unittest.mock import patch
        engine, _ = self.engine(True)
        for text in ("tea coffee", "mango", "banana"):
            self.remember(engine, text)
        engine.recall_bm25("tea")
        import mnemosis.bm25 as module
        original = module.tokenize
        calls = []
        def tracked(text):
            calls.append(text)
            return original(text)
        with patch.object(module, "tokenize", tracked):
            engine.recall_bm25("coffee")
        self.assertEqual(calls, ["coffee"])

    def test_dict_direct_content_edit_invalidates_index(self):
        engine, _ = self.engine()
        item = self.remember(engine, "tea")
        engine.recall_bm25("tea")
        # DictBackend historically exposes mutable MemoryItem references.
        item.content = "coffee"
        self.assertFalse(engine.recall_bm25("tea"))
        self.assertTrue(engine.recall_bm25("coffee"))

    def test_rollback_does_not_keep_uncommitted_terms(self):
        engine, _ = self.engine(True)
        item = self.remember(engine, "tea")
        engine.backend._conn.commit()
        engine.backend._conn.execute("UPDATE memories SET content='coffee' WHERE id=?", (item.id,))
        self.assertTrue(engine.recall_bm25("coffee"))
        engine.backend._conn.rollback()
        self.assertTrue(engine.recall_bm25("tea"))
        self.assertFalse(engine.recall_bm25("coffee"))

    def test_normalized_fusion_rejects_nonfinite_weights(self):
        engine, _ = self.engine()
        self.remember(engine, "tea")
        for argument in ("ng_weight", "cue_weight", "recency_weight", "dense_weight"):
            with self.subTest(argument=argument), self.assertRaises(ValueError):
                engine.recall_fused("tea", normalize_fusion=True, **{argument:float("nan")})

    def test_feedback_does_not_rebuild_sqlite_lexical_index(self):
        from unittest.mock import patch
        import mnemosis.bm25 as module
        engine, _ = self.engine(True)
        item = self.remember(engine, "tea coffee")
        engine.recall_bm25("tea")
        engine.record_feedback(item.id, useful=True)
        original=module.tokenize
        calls=[]
        def track(text):
            calls.append(text)
            return original(text)
        with patch.object(module,"tokenize",track):
            engine.recall_bm25("coffee")
        self.assertEqual(calls,["coffee"])


if __name__ == "__main__":
    unittest.main()
