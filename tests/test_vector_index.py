"""Tests for the zero-dependency LSH vector index."""

from __future__ import annotations

import math
import os
import random
import sqlite3
import sys
import tempfile
import threading
import unittest
from array import array
from unittest import mock

try:
    import numpy as np
except ImportError:  # CI unit-test job has no third-party dependencies
    np = None

from mnemosis.vector_index import VectorIndex


class VectorIndexTests(unittest.TestCase):
    def _sample(self) -> list[tuple[str, list[float]]]:
        vectors = [
            ("a", [1.0, 0.0, 0.0]),
            ("b", [0.9, 0.1, 0.0]),
            ("c", [0.0, 1.0, 0.0]),
            ("d", [0.0, 0.0, 1.0]),
        ]
        return vectors

    def test_add_and_search_returns_closest(self) -> None:
        index = VectorIndex(dim=3, bits=8, buckets_per_item=2)
        for memory_id, vector in self._sample():
            index.add(memory_id, vector)
        results = index.search([1.0, 0.05, 0.0], top_k=2)
        self.assertEqual(results[0][0], "a")
        self.assertGreaterEqual(results[0][1], results[1][1])
        self.assertAlmostEqual(results[0][1], 0.999, places=2)
        index.close()

    def test_add_many_batches_vectors(self) -> None:
        index = VectorIndex(dim=3, bits=8, buckets_per_item=2)
        entries = [
            (f"m{position}", [1.0 - position * 0.01, 0.0, 0.0])
            for position in range(20)
        ]
        index.add_many(entries)
        self.assertEqual(index.size, 20)
        results = index.search([1.0, 0.0, 0.0], top_k=3)
        self.assertEqual(results[0][0], "m0")
        index.close()

    def test_readd_same_id_does_not_duplicate_buckets(self) -> None:
        index = VectorIndex(dim=3, bits=8, buckets_per_item=3)
        index.add("a", [1.0, 0.0, 0.0])
        index.add("a", [0.0, 1.0, 0.0])
        count = index._conn.execute(
            "SELECT COUNT(*) FROM buckets WHERE memory_id = 'a'"
        ).fetchone()[0]
        self.assertEqual(count, 3)
        index.add_many([("a", [0.0, 0.0, 1.0])])
        count = index._conn.execute(
            "SELECT COUNT(*) FROM buckets WHERE memory_id = 'a'"
        ).fetchone()[0]
        self.assertEqual(count, 3)
        index.close()

    def test_has_reports_vector_presence(self) -> None:
        index = VectorIndex(dim=3, bits=8, buckets_per_item=2)
        self.assertFalse(index.has("a"))
        index.add("a", [1.0, 0.0, 0.0])
        self.assertTrue(index.has("a"))
        index.close()

    def test_remove_drops_vectors_and_buckets(self) -> None:
        index = VectorIndex(dim=3, bits=8, buckets_per_item=2)
        for memory_id, vector in self._sample():
            index.add(memory_id, vector)
        self.assertEqual(index.size, 4)
        self.assertEqual(index.remove(["a", "c"]), 2)
        self.assertEqual(index.size, 2)
        self.assertFalse(index.has("a"))
        self.assertFalse(index.has("c"))
        results = index.search([1.0, 0.05, 0.0], top_k=2)
        self.assertNotIn("a", {memory_id for memory_id, _ in results})
        bucket_count = index._conn.execute(
            "SELECT COUNT(*) FROM buckets WHERE memory_id IN ('a', 'c')"
        ).fetchone()[0]
        self.assertEqual(bucket_count, 0)
        index.close()

    def test_remove_is_idempotent_and_chunked(self) -> None:
        index = VectorIndex(dim=3, bits=8, buckets_per_item=2)
        entries = [
            (f"m{position}", [1.0, 0.0, 0.0])
            for position in range(600)
        ]
        index.add_many(entries)
        self.assertEqual(index.size, 600)
        self.assertEqual(index.remove(["missing", "m0"]), 1)
        self.assertEqual(index.remove(["m0"]), 0)
        self.assertEqual(index.remove([f"m{i}" for i in range(600)]), 599)
        self.assertEqual(index.size, 0)
        index.close()

    def test_persists_across_reopen(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index.sqlite")
            index = VectorIndex(path, dim=3, bits=8)
            index.add("x", [1.0, 0.0, 0.0])
            index.close()
            index2 = VectorIndex(path, dim=3, bits=8)
            results = index2.search([1.0, 0.0, 0.0], top_k=1)
            self.assertEqual(results[0][0], "x")
            index2.close()

    def test_scale_smoke(self) -> None:
        index = VectorIndex(dim=8, bits=16, buckets_per_item=4)
        for i in range(500):
            vector = [math.sin(i + j) for j in range(8)]
            index.add(f"m{i}", vector)
        results = index.search([math.sin(123 + j) for j in range(8)], top_k=5)
        self.assertEqual(len(results), 5)
        self.assertEqual(index.size, 500)
        index.close()

    @unittest.skipIf(np is None, "numpy required")
    def test_exact_scan_matches_bruteforce_topk(self) -> None:
        """Medium stores must be exact (regression: LSH recall collapse)."""
        rng = random.Random(42)
        entries = [
            (
                f"m{i}",
                [rng.uniform(-1.0, 1.0) for _ in range(16)],
            )
            for i in range(2000)
        ]
        query = [rng.uniform(-1.0, 1.0) for _ in range(16)]
        index = VectorIndex(
            dim=16,
            bits=13,
            buckets_per_item=8,
            full_scan_threshold=50,  # legacy threshold does NOT cover 2000
        )
        index.add_many(entries)
        results = index.search(query, top_k=5)
        self.assertEqual(len(results), 5)

        matrix = np.asarray([v for _, v in entries], dtype=np.float32)
        q = np.asarray(query, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1)
        scores = matrix @ q / (norms * np.linalg.norm(q) + 1e-9)
        expected = [
            (f"m{int(i)}", float(scores[i]))
            for i in np.argsort(-scores)[:5]
        ]
        self.assertEqual(
            [memory_id for memory_id, _ in results],
            [memory_id for memory_id, _ in expected],
        )
        for (_, got), (_, want) in zip(results, expected):
            self.assertAlmostEqual(got, want, places=5)
        index.close()

    def test_exact_scan_limit_forces_lsh_path(self) -> None:
        """Above exact_scan_limit the bucket path must still work."""
        entries = [
            (
                f"m{i}",
                [math.sin(i + j) / (1.0 + i % 7) for j in range(8)],
            )
            for i in range(500)
        ]
        index = VectorIndex(
            dim=8,
            bits=16,
            buckets_per_item=8,
            full_scan_threshold=50,
            exact_scan_limit=100,
        )
        index.add_many(entries)
        results = index.search([math.sin(123 + j) for j in range(8)], top_k=5)
        self.assertEqual(len(results), 5)
        # Exact path caches the matrix; LSH path does not.
        self.assertIsNone(index._matrix_cache)
        index.close()

    def test_exact_scan_respects_byte_budget(self) -> None:
        entries = [
            (f"m{i}", [1.0 - i * 0.001, 0.0, 0.0]) for i in range(200)
        ]
        strict = VectorIndex(
            dim=3,
            full_scan_threshold=0,
            exact_scan_max_bytes=100,
        )
        strict.add_many(entries)
        strict.search([1.0, 0.0, 0.0], top_k=3)
        self.assertIsNone(strict._matrix_cache)
        strict.close()

        roomy = VectorIndex(
            dim=3,
            full_scan_threshold=0,
            exact_scan_max_bytes=1024 * 1024,
        )
        roomy.add_many(entries)
        roomy.search([1.0, 0.0, 0.0], top_k=3)
        self.assertIsNotNone(roomy._matrix_cache)
        roomy.close()

    def test_search_empty_store_returns_empty(self) -> None:
        index = VectorIndex()
        self.assertEqual(index.search([1.0, 0.0, 0.0], top_k=3), [])
        index.close()

    def test_legacy_store_without_meta_infers_dim(self) -> None:
        index = VectorIndex()
        index._conn.execute(
            "INSERT INTO vectors (memory_id, vec) VALUES (?, ?)",
            ("x", array("d", [1.0, 0.0, 0.0]).tobytes()),
        )
        index._conn.commit()
        results = index.search([1.0, 0.0, 0.0], top_k=1)
        self.assertEqual(results[0][0], "x")
        self.assertEqual(index._dim, 3)
        index.close()

    def test_query_dimension_mismatch_raises(self) -> None:
        index = VectorIndex(dim=3)
        index.add("a", [1.0, 0.0, 0.0])
        with self.assertRaisesRegex(ValueError, "does not match"):
            index.search([1.0, 0.0, 0.0, 0.0], top_k=1)
        index.close()

    def test_concurrent_add_search_smoke(self) -> None:
        index = VectorIndex(dim=4)
        errors: list[str] = []

        def worker(tid: int) -> None:
            try:
                for i in range(50):
                    index.add(
                        f"t{tid}-{i}",
                        [1.0, float(tid), float(i), 0.0],
                    )
                    index.search([1.0, 1.0, 1.0, 0.0], top_k=3)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"t{tid}: {exc!r}")

        threads = [
            threading.Thread(target=worker, args=(tid,)) for tid in range(4)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(errors, [])
        self.assertEqual(index.size, 200)
        index.close()

    def test_lsh_out_of_budget_returns_best_effort(self) -> None:
        """Above the exact budget LSH must not blow memory with full scans."""
        rng = random.Random(7)
        entries = [
            (
                f"m{i}",
                [rng.uniform(-1.0, 1.0) for _ in range(12)],
            )
            for i in range(2000)
        ]
        query = [rng.uniform(-1.0, 1.0) for _ in range(12)]
        index = VectorIndex(
            dim=12,
            bits=20,
            buckets_per_item=4,
            full_scan_threshold=0,
            exact_scan_limit=0,  # force the LSH path for every query
        )
        index.add_many(entries)
        with self.assertLogs("mnemosis.vector_index", level="WARNING"):
            results = index.search(query, top_k=5)
        self.assertLessEqual(len(results), 5)
        scores = [score for _, score in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertTrue(
            all(memory_id.startswith("m") for memory_id, _ in results)
        )
        index.close()

    @unittest.skipIf(np is None, "numpy required")
    def test_lsh_fallback_to_full_scan_optin_matches_bruteforce(self) -> None:
        """fallback_to_full_scan=True restores exact recall out of budget."""
        rng = random.Random(7)
        entries = [
            (
                f"m{i}",
                [rng.uniform(-1.0, 1.0) for _ in range(12)],
            )
            for i in range(2000)
        ]
        query = [rng.uniform(-1.0, 1.0) for _ in range(12)]
        index = VectorIndex(
            dim=12,
            bits=20,
            buckets_per_item=4,
            full_scan_threshold=0,
            exact_scan_limit=0,
            fallback_to_full_scan=True,
        )
        index.add_many(entries)
        results = index.search(query, top_k=5)
        matrix = np.asarray([v for _, v in entries], dtype=np.float32)
        q = np.asarray(query, dtype=np.float32)
        scores = matrix @ q / (
            np.linalg.norm(matrix, axis=1) * np.linalg.norm(q) + 1e-9
        )
        expected = [f"m{int(i)}" for i in np.argsort(-scores)[:5]]
        self.assertEqual(
            [memory_id for memory_id, _ in results], expected
        )
        index.close()

    def test_reads_legacy_float64_blobs(self) -> None:
        """Old .vec files stored float64; they must still load exactly."""
        index = VectorIndex(dim=3)
        index._projection()  # persist meta so dim is known on reopen
        index._conn.execute(
            "INSERT INTO vectors (memory_id, vec) VALUES (?, ?)",
            ("a", array("d", [1.0, 0.0, 0.0]).tobytes()),
        )
        index._conn.execute(
            "INSERT INTO vectors (memory_id, vec) VALUES (?, ?)",
            ("b", array("d", [0.9, 0.1, 0.0]).tobytes()),
        )
        index._conn.execute(
            "INSERT INTO vectors (memory_id, vec) VALUES (?, ?)",
            ("c", array("d", [0.0, 1.0, 0.0]).tobytes()),
        )
        index._conn.commit()
        results = index.search([1.0, 0.0, 0.0], top_k=2)
        self.assertEqual([mid for mid, _ in results], ["a", "b"])
        self.assertTrue(
            all(math.isfinite(score) for _, score in results)
        )
        index.close()

    def test_remove_invalidates_matrix_and_count_caches(self) -> None:
        index = VectorIndex(dim=3)
        for memory_id, vector in self._sample():
            index.add(memory_id, vector)
        index.search([1.0, 0.0, 0.0], top_k=2)  # builds the matrix cache
        self.assertIsNotNone(index._matrix_cache)
        self.assertEqual(index._count, 4)
        index.remove(["a"])
        self.assertIsNone(index._matrix_cache)
        self.assertIsNone(index._count)
        self.assertEqual(index.size, 3)
        index.close()

    def test_clear_resets_dimension(self) -> None:
        index = VectorIndex(dim=3)
        index.add("a", [1.0, 0.0, 0.0])
        index.clear()
        index.add("b", [1.0, 0.0])  # different dim after clear
        results = index.search([1.0, 0.0], top_k=1)
        self.assertEqual(results[0][0], "b")
        index.close()

    def test_size_count_is_cached_between_searches(self) -> None:
        class SpyConnection(sqlite3.Connection):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.count_calls = 0

            def execute(self, sql, *args, **kwargs):
                if str(sql).startswith(
                    "SELECT COUNT(*) FROM vectors"
                ):
                    self.count_calls += 1
                return super().execute(sql, *args, **kwargs)

        real_connect = sqlite3.connect

        def factory(path, **kwargs):
            return real_connect(path, factory=SpyConnection, **kwargs)

        with mock.patch(
            "mnemosis.vector_index.sqlite3.connect", side_effect=factory
        ):
            index = VectorIndex(dim=3)
            for memory_id, vector in self._sample():
                index.add(memory_id, vector)
            index.search([1.0, 0.0, 0.0], top_k=2)
            index.search([0.0, 1.0, 0.0], top_k=2)
            self.assertEqual(index._conn.count_calls, 1)
            index.close()

    def test_no_numpy_path_reuses_cached_rows(self) -> None:
        class SpyConnection(sqlite3.Connection):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.full_scans = 0

            def execute(self, sql, *args, **kwargs):
                if str(sql).strip().startswith(
                    "SELECT memory_id, vec FROM vectors"
                ):
                    self.full_scans += 1
                return super().execute(sql, *args, **kwargs)

        real_connect = sqlite3.connect

        def factory(path, **kwargs):
            return real_connect(path, factory=SpyConnection, **kwargs)

        with mock.patch(
            "mnemosis.vector_index.sqlite3.connect", side_effect=factory
        ), mock.patch.dict(sys.modules, {"numpy": None}):
            index = VectorIndex(dim=3)
            for memory_id, vector in self._sample():
                index.add(memory_id, vector)
            index.search([1.0, 0.0, 0.0], top_k=2)
            index.search([0.0, 1.0, 0.0], top_k=2)
            self.assertEqual(index._conn.full_scans, 1)
            index.close()

    def test_lsh_candidate_cap_keeps_topk(self) -> None:
        rng = random.Random(3)
        entries = [
            (
                f"m{i}",
                [rng.uniform(-1.0, 1.0) for _ in range(8)],
            )
            for i in range(2000)
        ]
        query = [rng.uniform(-1.0, 1.0) for _ in range(8)]
        index = VectorIndex(
            dim=8,
            bits=8,
            buckets_per_item=32,
            full_scan_threshold=0,
            exact_scan_limit=0,
            max_candidates=5,
        )
        index.add_many(entries)
        results = index.search(query, top_k=10)
        self.assertEqual(len(results), 10)
        index.close()

    def test_reopen_without_dim_loads_meta(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "index.sqlite")
            index = VectorIndex(path, dim=3)
            index.add("x", [1.0, 0.0, 0.0])
            index.close()
            reopened = VectorIndex(path)  # dim comes from persisted meta
            results = reopened.search([1.0, 0.0, 0.0], top_k=1)
            self.assertEqual(results[0][0], "x")
            reopened.close()


if __name__ == "__main__":
    unittest.main()
