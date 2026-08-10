"""Tests for the persistent SQLite embedding cache and dense fast path."""

from __future__ import annotations

import os
import tempfile
import unittest

from mnemosis import MemoryEngine
from mnemosis.embedding import Embedder
from mnemosis.embedding_cache import SqliteEmbeddingCache
from mnemosis.hybrid import _dense_results
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class _CountingEmbedder(Embedder):
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return [float(len(text)), 1.0]


class _FakeDense(Embedder):
    def embed(self, text: str) -> list[float]:
        base = [0.0] * 4
        if "hiking" in text or "mountains" in text:
            base[0] = 1.0
        if "sunny" in text or "weather" in text:
            base[1] = 1.0
        if "pizza" in text or "food" in text:
            base[2] = 1.0
        return base


class EmbeddingCacheTests(unittest.TestCase):
    def test_sqlite_cache_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "vectors.sqlite")
            inner = _CountingEmbedder()
            cache = SqliteEmbeddingCache(inner, path)
            first = cache.embed("hello world")
            second = cache.embed("hello world")
            self.assertEqual(first, second)
            self.assertEqual(inner.calls, 1)
            cache.close()

            inner2 = _CountingEmbedder()
            cache2 = SqliteEmbeddingCache(inner2, path)
            self.assertEqual(cache2.embed("hello world"), first)
            self.assertEqual(inner2.calls, 0)  # loaded from disk
            cache2.close()

    def test_sqlite_cache_lru_eviction(self) -> None:
        cache = SqliteEmbeddingCache(_CountingEmbedder(), ":memory:", max_memory=2)
        cache.embed("one")
        cache.embed("two")
        cache.embed("three")
        self.assertEqual(len(cache._memory), 2)
        self.assertNotIn("one", cache._memory)
        cache.close()

    def test_sqlite_cache_rejects_bad_table_name(self) -> None:
        with self.assertRaises(ValueError):
            SqliteEmbeddingCache(
                _CountingEmbedder(),
                ":memory:",
                table="vectors; DROP TABLE x",
            )

    def test_sqlite_cache_context_manager(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "ctx.sqlite")
            with SqliteEmbeddingCache(_CountingEmbedder(), path) as cache:
                self.assertEqual(cache.embed("ctx text"), [8.0, 1.0])

    def test_dense_results_topk_and_order(self) -> None:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        for text in (
            "I love hiking in the mountains.",
            "The weather is sunny today.",
            "My favorite food is pizza.",
        ):
            engine.remember(
                text,
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.5,
            )
        results = _dense_results(engine, "I love hiking", None, _FakeDense(), 2)
        self.assertEqual(len(results), 2)
        self.assertIn("hiking", results[0].item.content)
        self.assertGreaterEqual(results[0].score, results[1].score)

    def test_fused_recall_skips_zero_weight_passes(self) -> None:
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "Alice booked a flight to Tokyo.",
            kind=MemoryKind.EPISODIC,
            source=source,
        )
        engine.remember(
            "Bob prefers tea over coffee.",
            kind=MemoryKind.EPISODIC,
            source=source,
        )

        class _AliceDense(Embedder):
            def embed(self, text: str) -> list[float]:
                return [1.0, 0.0] if "Alice" in text else [0.0, 1.0]

        results = engine.recall_fused(
            "Who booked a flight?",
            top_k=2,
            kw_weight=0.0,
            ng_weight=0.0,
            dense_embedder=_AliceDense(),
            dense_weight=1.0,
            recency_weight=0.0,
            cue_weight=0.0,
            date_weight=0.0,
        )
        self.assertTrue(any("Alice" in r.item.content for r in results))


if __name__ == "__main__":
    unittest.main()
