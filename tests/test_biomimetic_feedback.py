"""Regression tests for retrieval learning boundaries and evidence lineage."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from datetime import timedelta

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


if __name__ == "__main__":
    unittest.main()
