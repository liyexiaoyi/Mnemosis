"""Rare-cue specificity must not count coverage a second time."""
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from mnemosis import MemoryEngine, MemoryKind, SourceRecord, SourceType
from mnemosis import lexical_cues

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


class MeanSpecificityTests(unittest.TestCase):
    def scale(self, *args):
        helper = getattr(lexical_cues, "_mean_idf_scale", None)
        self.assertIsNotNone(helper, "mean specificity normalization is missing")
        return helper(*args)

    def test_uniform_positive_weights_do_not_reward_hit_count_again(self):
        for h in (1, 2, 3):
            with self.subTest(h=h):
                self.assertEqual(self.scale(4*h, 12, 3, h), 1.0)

    def test_tiny_uniform_weights_remain_neutral(self):
        for h in (1, 2, 3):
            with self.subTest(h=h):
                self.assertAlmostEqual(self.scale(1e-12*h, 3e-12, 3, h), 1.0)

    def test_relative_specificity_distinguishes_rare_and_common_matches(self):
        # Query weights [4, 1, 1]; hand-computed means, independent of helper.
        for hit_weight, h, want in ((4, 1, 1.5), (1, 1, .75), (5, 2, 1.125), (6, 3, 1.0)):
            with self.subTest(hit_weight=hit_weight, h=h):
                self.assertEqual(self.scale(hit_weight, 6, 3, h), want)

    def test_common_weight_rescaling_preserves_specificity(self):
        for multiplier in (1e-200, 1e-12, 1, 1e200):
            with self.subTest(multiplier=multiplier):
                self.assertAlmostEqual(self.scale(4*multiplier, 6*multiplier, 3, 1), 1.5)

    def test_zero_guards_and_specificity_limits(self):
        for args, want in (((0, 0, 3, 1), 1.0), ((0, 4, 3, 0), 1.0),
                           ((0, 4, 3, 1), .5), ((4, 4, 10, 1), 2.0)):
            with self.subTest(args=args):
                self.assertEqual(self.scale(*args), want)


class MeanSpecificityRecallTests(unittest.TestCase):
    def engine(self, disk, populations):
        path = None
        if disk:
            tmp = tempfile.TemporaryDirectory()
            self.addCleanup(tmp.cleanup)
            path = str(Path(tmp.name) / "memory.sqlite")
        engine = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(engine.close)
        items = engine.store.remember_many([
            dict(content=text, kind=MemoryKind.EPISODIC,
                 source=SourceRecord(SourceType.USER), created_at=NOW,
                 importance=.5, cues=[])
            for text, count in populations for _ in range(count)
        ])
        return engine, items

    def recall(self, engine, query, **kwargs):
        return engine.store.recall(query, now=NOW, read_only=True,
            lexical_policy="inflection", top_k=3, source_trust_boost=False,
            confidence_boost=False, kind_preference=False, temporal_reason=False,
            reasoning_pack=False, pattern_completion=False, **kwargs)

    def test_equal_capped_idf_keeps_geometric_overlap_on_real_backends(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine, _ = self.engine(disk, [("tango unrelated", 1),
                    ("tango violet unrelated", 1), ("tango violet glacier", 1),
                    ("weather background", 997)])
                rows = {r.item.content: r.score for r in self.recall(engine, "tango violet glacier")}
                # All three positive RSJ weights cap at 4. Scores contain
                # .25 fresh retrievability + .20 * .5 importance + .40 overlap.
                for text, want in (("tango unrelated", .5132993161855453),
                    ("tango violet unrelated", .6166666666666667),
                    ("tango violet glacier", .75)):
                    self.assertAlmostEqual(rows[text], want)

    def test_zero_weight_hit_is_discounted_when_other_query_cue_is_rare(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine, items = self.engine(disk, [("tango unrelated", 1),
                    ("tango weather", 997), ("violet glacier", 2)])
                results = self.recall(engine, "tango violet",
                    exclude_ids={i.id for i in items[1:]})
                self.assertEqual([r.item.id for r in results], [items[0].id])
                self.assertAlmostEqual(results[0].score, .45)

    def test_all_zero_weights_keep_overlap_without_division(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine, items = self.engine(disk, [("tango unrelated", 1),
                                                 ("tango weather", 999)])
                results = self.recall(engine, "tango violet",
                    exclude_ids={i.id for i in items[1:]})
                self.assertEqual([r.item.id for r in results], [items[0].id])
                self.assertAlmostEqual(results[0].score, .55)


if __name__ == "__main__":
    unittest.main()
