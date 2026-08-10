"""Tests for the persistent SQLite embedding cache and dense fast path."""

from __future__ import annotations

import os
import tempfile

import pytest

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


def test_sqlite_cache_roundtrip() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "vectors.sqlite")
        inner = _CountingEmbedder()
        cache = SqliteEmbeddingCache(inner, path)
        first = cache.embed("hello world")
        second = cache.embed("hello world")
        assert first == second
        assert inner.calls == 1
        cache.close()

        inner2 = _CountingEmbedder()
        cache2 = SqliteEmbeddingCache(inner2, path)
        assert cache2.embed("hello world") == first
        assert inner2.calls == 0  # loaded from disk, no embedding call
        cache2.close()


def test_sqlite_cache_lru_eviction() -> None:
    inner = _CountingEmbedder()
    cache = SqliteEmbeddingCache(inner, ":memory:", max_memory=2)
    cache.embed("one")
    cache.embed("two")
    cache.embed("three")
    assert len(cache._memory) == 2
    assert "one" not in cache._memory
    cache.close()


def test_sqlite_cache_rejects_bad_table_name() -> None:
    inner = _CountingEmbedder()
    with pytest.raises(ValueError):
        SqliteEmbeddingCache(inner, ":memory:", table="vectors; DROP TABLE x")


def test_sqlite_cache_context_manager() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "ctx.sqlite")
        inner = _CountingEmbedder()
        with SqliteEmbeddingCache(inner, path) as cache:
            assert cache.embed("ctx text") == [8.0, 1.0]


def test_dense_results_topk_and_order() -> None:
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

    class _FakeDense(Embedder):
        def embed(self, text: str) -> list[float]:
            # Deterministic vector: shares a feature with "hiking" queries.
            base = [0.0] * 4
            if "hiking" in text or "mountains" in text:
                base[0] = 1.0
            if "sunny" in text or "weather" in text:
                base[1] = 1.0
            if "pizza" in text or "food" in text:
                base[2] = 1.0
            return base

    results = _dense_results(engine, "I love hiking", None, _FakeDense(), 2)
    assert len(results) == 2
    assert "hiking" in results[0].item.content
    assert results[0].score >= results[1].score


def test_fused_recall_skips_zero_weight_passes() -> None:
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

    class _FakeDense(Embedder):
        def embed(self, text: str) -> list[float]:
            return [1.0, 0.0] if "Alice" in text else [0.0, 1.0]

    results = engine.recall_fused(
        "Who booked a flight?",
        top_k=2,
        kw_weight=0.0,
        ng_weight=0.0,
        dense_embedder=_FakeDense(),
        dense_weight=1.0,
        recency_weight=0.0,
        cue_weight=0.0,
        date_weight=0.0,
    )
    assert any("Alice" in r.item.content for r in results)
