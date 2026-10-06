"""Memory-population weighting of the legacy smoothed discrepancy statistic."""
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType

NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)


class CalibrationWeightingTest(unittest.TestCase):
    def engine(self, disk):
        path = None
        if disk:
            temp = tempfile.TemporaryDirectory()
            self.addCleanup(temp.cleanup)
            path = str(Path(temp.name) / "memory.sqlite")
        engine = MemoryEngine(path, auto_warmup=False)
        self.addCleanup(engine.close)
        return engine

    def items(self, high=2, low=1):
        return [MemoryItem(
            content=f"{name} memory {i}", kind=MemoryKind.SEMANTIC,
            source=SourceRecord(SourceType.USER), created_at=NOW,
            confidence=confidence, access_count=3,
            retrieval_successes=hits, retrieval_failures=fails,
        ) for name, count, confidence, hits, fails in
            (("high", high, 1.0, 0, 4), ("low", low, .1, 4, 0))
            for i in range(count)]

    def test_unequal_buckets_use_memory_population_not_equal_bucket_weights(self):
        # Hand oracle: 2/1 => (2*.86 + (5/6-.096))/3 = .819111...
        # 10/1 => (10*(.96-1/42) + (5/6-.096))/11 = .918112...
        for disk in (False, True):
            for high, want in ((2, .8191), (10, .9181)):
                with self.subTest(disk=disk, high=high):
                    engine = self.engine(disk)
                    items = self.items(high=high)
                    engine.backend.add_many(items)
                    rows = engine.backend.list_items()
                    predictions = {i.id: engine.meta.confidence(i, NOW)[1] for i in rows}
                    self.assertEqual([predictions[i.id] for i in items], [.96]*high + [.096])
                    self.assertEqual(engine.meta.calibration_stats(rows, NOW)["ece"], want)

    def test_unobserved_bucket_is_reported_but_excluded_from_weighted_total(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                items = self.items()
                unknown = MemoryItem(content="unknown history", kind=MemoryKind.SEMANTIC,
                    source=SourceRecord(SourceType.USER), created_at=NOW,
                    confidence=.5, access_count=3)
                engine.backend.add_many([*items, unknown])
                stats = engine.meta.calibration_stats(engine.backend.list_items(), NOW)
                self.assertEqual(stats["ece"], .8191)
                self.assertEqual(stats["buckets"][1], {
                    "predicted_bucket": "0.4-0.6", "n_items": 1,
                    "mean_predicted": .48, "empirical_hit_rate": None})

    def test_empty_and_no_history_keep_zero_sentinel(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                self.assertEqual(engine.meta.calibration_stats([], NOW), {"buckets": [], "ece": 0.0})
                items = self.items()
                for item in items:
                    item.retrieval_successes = item.retrieval_failures = 0
                stats = engine.meta.calibration_stats(items, NOW)
                self.assertEqual(stats["ece"], 0.0)
                self.assertTrue(all(row["empirical_hit_rate"] is None for row in stats["buckets"]))

    def test_single_bucket_preserves_pooled_beta_prior(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                items = self.items(low=0)
                for item in items:
                    item.retrieval_successes, item.retrieval_failures = 4, 0
                # One prior for the pooled bucket: (8+1)/(8+2)=.9.
                self.assertEqual(engine.meta.calibration_stats(items, NOW), {
                    "buckets": [{"predicted_bucket": "0.8-1.0", "n_items": 2,
                        "mean_predicted": .96, "empirical_hit_rate": .9}], "ece": .06})

    def test_input_order_does_not_change_weighted_result(self):
        for disk in (False, True):
            engine = self.engine(disk)
            items = self.items()
            for order in ((0, 1, 2), (2, 1, 0), (1, 2, 0)):
                with self.subTest(disk=disk, order=order):
                    self.assertEqual(engine.meta.calibration_stats([items[i] for i in order], NOW), {
                        "buckets": [
                            {"predicted_bucket": "0.0-0.2", "n_items": 1,
                             "mean_predicted": .096, "empirical_hit_rate": .833},
                            {"predicted_bucket": "0.8-1.0", "n_items": 2,
                             "mean_predicted": .96, "empirical_hit_rate": .1}], "ece": .8191})

    def test_legacy_counts_remain_separate_from_verified_feedback_and_read_only(self):
        for disk in (False, True):
            with self.subTest(disk=disk):
                engine = self.engine(disk)
                items = self.items()
                # Opposite verified feedback must not replace legacy counters.
                for item in items:
                    item.verified_successes = 100 if item.confidence == 1 else 0
                    item.verified_failures = 100 if item.confidence < 1 else 0
                engine.backend.add_many(items)
                engine.backend.add_link(items[0].id, items[-1].id, .5)
                def snapshot():
                    return deepcopy((
                        [i.to_dict() for i in engine.backend.list_items()],
                        engine.backend.all_links(), engine._recall_log))
                def sqlite_state():
                    conn = engine.backend._conn
                    return (conn.total_changes, conn.in_transaction,
                        conn.execute("PRAGMA data_version").fetchone()[0],
                        conn.execute("PRAGMA schema_version").fetchone()[0],
                        conn.execute("PRAGMA temp.schema_version").fetchone()[0])
                before = snapshot()
                guard = sqlite_state() if disk else None
                self.assertEqual(engine.meta.calibration_stats(engine.backend.list_items(), NOW)["ece"], .8191)
                self.assertEqual(snapshot(), before)
                if disk:
                    self.assertEqual(sqlite_state(), guard)


if __name__ == "__main__":
    unittest.main()
