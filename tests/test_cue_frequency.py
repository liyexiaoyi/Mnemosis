"""Skipped common postings must never invent rare word-form evidence."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from mnemosis import MemoryEngine, MemoryKind, SourceRecord, SourceType

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


class CueFrequencyTests(unittest.TestCase):
    def engine(self, disk, populations):
        path = None
        if disk:
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            path = str(Path(tmp.name) / "memory.sqlite")
        engine = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(engine.close)
        engine.store.remember_many([
            dict(content=text, kind=MemoryKind.EPISODIC,
                 source=SourceRecord(SourceType.USER), created_at=NOW,
                 importance=.5, cues=[])
            for text, count in populations for _ in range(count)
        ])
        return engine

    def recall(self, engine, query, **kwargs):
        return engine.recall(query, now=NOW, read_only=True, top_k=5,
                             lexical_policy="inflection", **kwargs)

    def test_common_family_cannot_displace_discriminative_candidates(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk, [("friend", 6000), ("friends", 150),
                                           ("orchid", 200), ("weather", 3650)])
                before = [i.to_dict() for i in engine.store.all_active()]
                with patch.object(engine.backend, "find_by_terms",
                                  wraps=engine.backend.find_by_terms) as postings, \
                     patch.object(engine.backend, "get_many",
                                  wraps=engine.backend.get_many) as loads:
                    results = self.recall(engine, "friends orchid")
                self.assertEqual([r.item.content for r in results], ["orchid"] * 5)
                queried = {term for call in postings.call_args_list for term in call.args[0]}
                self.assertNotIn("friend", queried)
                self.assertTrue(all(len(call.args[0]) <= 100 for call in loads.call_args_list))
                self.assertEqual([i.to_dict() for i in engine.store.all_active()], before)
                self.assertEqual(engine.backend.all_links(), [])
                self.assertEqual(engine.get_recall_log(), [])

    def test_posting_guard_boundary_preserves_common_family_weight(self):
        for disk in (False, True):
            for common_count in (4999, 5000, 5001):
                with self.subTest(disk=disk, common_count=common_count):
                    engine = self.engine(disk, [("friend", common_count), ("friends", 150),
                        ("orchid", 200), ("weather", 9650-common_count)])
                    with patch.object(engine.backend, "find_by_terms",
                                      wraps=engine.backend.find_by_terms) as postings:
                        results = self.recall(engine, "friends orchid")
                    self.assertEqual([r.item.content for r in results], ["orchid"] * 5)
                    queried = {term for call in postings.call_args_list for term in call.args[0]}
                    self.assertEqual("friend" in queried, common_count <= 5000)

    def test_complete_postings_use_union_not_sum_for_overlapping_forms(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                # The family occupies 200 records, not the sum of 400 postings.
                engine = self.engine(disk, [("friend friends", 200),
                                           ("orchid", 300), ("weather", 500)])
                self.assertEqual([r.item.content for r in self.recall(engine, "friends orchid")],
                                 ["friend friends"] * 5)

    def test_multiple_skipped_forms_cannot_hide_disjoint_family_frequency(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                # Each skipped form is below half of the corpus; their union
                # exceeds half. Taking only the maximum df would be unsafe.
                engine = self.engine(disk, [("friend", 6000), ("friends", 6000),
                    ("friending", 150), ("orchid", 3000), ("weather", 4850)])
                results = self.recall(engine, "friends orchid")
                reference = self.recall(engine, "unseen orchid")
                self.assertEqual([r.item.id for r in results], [r.item.id for r in reference])
                for actual, expected in zip(results, reference):
                    self.assertAlmostEqual(actual.score, expected.score)

    def test_large_corpus_default_stays_explicit_literal(self):
        engine = self.engine(False, [("friend", 6000), ("friends", 150),
                                     ("orchid", 200), ("weather", 3650)])
        default = engine.recall("friends orchid", now=NOW, read_only=True, top_k=5)
        explicit = engine.recall("friends orchid", now=NOW, read_only=True,
                                top_k=5, lexical_policy="literal")
        self.assertEqual([(r.item.id, r.score, r.reasons) for r in default],
                         [(r.item.id, r.score, r.reasons) for r in explicit])


if __name__ == "__main__":
    unittest.main()
