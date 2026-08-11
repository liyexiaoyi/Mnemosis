"""Tests for the zero-dependency LSH vector index."""

from __future__ import annotations

import math
import os
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
