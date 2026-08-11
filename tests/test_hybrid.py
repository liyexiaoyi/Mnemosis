"""Tests for fused multi-path retrieval (hybrid.py)."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.embedding import Embedder
from mnemosis.hybrid import (
    _DENSE_FULL_SCAN_LIMIT,
    _dense_results,
    english_inflections,
    rrf_scores,
    temporal_intent,
)
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _engine_with(*texts: str) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for index, text in enumerate(texts):
        engine.remember(
            text,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[f"sid:session{index}", f"date:2023-0{index + 1}-10"],
            importance=0.5,
        )
    return engine


class _TaggedEmbedder(Embedder):
    """Embedder that records every text it embeds."""

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.seen: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.seen.append(text)
        return [1.0, 0.0]


class _CountingEmbedder(Embedder):
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        return [1.0, 0.0]


class _BigStore:
    """Fake store with more active memories than the dense scan threshold."""

    def all_active(self, kind=None):
        return [object() for _ in range(_DENSE_FULL_SCAN_LIMIT + 1)]


class _FakeEngine:
    def __init__(self) -> None:
        self.store = _BigStore()


class HybridRetrievalTests(unittest.TestCase):
    def test_english_inflections(self) -> None:
        expanded = english_inflections(
            {"followers", "experienced", "weeks", "car"}
        )
        self.assertIn("follower", expanded)
        self.assertIn("experience", expanded)
        self.assertIn("week", expanded)
        self.assertIn("car", expanded)

    def test_temporal_intent(self) -> None:
        self.assertEqual(
            temporal_intent("What was the first issue I had?")["direction"],
            "oldest",
        )
        self.assertEqual(
            temporal_intent("What is my current address?")["direction"],
            "newest",
        )
        hints = temporal_intent("What happened after 2023/04/10?")
        self.assertEqual(hints["direction"], "newest")
        self.assertEqual(hints["after"].year, 2023)
        # "may" as a modal verb must not be treated as the month of May.
        self.assertNotIn("month", temporal_intent("I may go to the store"))
        self.assertEqual(temporal_intent("I visited in May 5")["month"], 5)

    def test_rrf_ranks_shared_winners_first(self) -> None:
        fused = rrf_scores(
            [["a", "b", "c"], ["a", "b", "c"]],
            k=60,
        )
        self.assertGreater(fused["a"], fused["b"])
        self.assertGreater(fused["b"], fused["c"])
        fused2 = rrf_scores([["a", "b"], ["a", "b"]], k=60)
        fused3 = rrf_scores([["b", "a"], ["c", "a"]], k=60)
        self.assertGreater(fused2["a"], fused3["a"])

    def test_fused_recall_keeps_top_keyword_hit(self) -> None:
        engine = _engine_with(
            "I bought a red bicycle on March 5th and rode it to work.",
            "We discussed holiday plans for summer.",
            "The red bike got a flat tire last week.",
        )
        results = engine.recall_fused(
            "What happened to my red bicycle?", top_k=2
        )
        contents = [r.item.content for r in results]
        self.assertTrue(any("bicycle" in c for c in contents))
        self.assertTrue(any("flat tire" in c for c in contents))

    def test_fused_recall_dedupes(self) -> None:
        engine = _engine_with(
            "I prefer dark roast coffee with no sugar.",
            "My favorite movie is Interstellar.",
        )
        results = engine.recall_fused("What coffee do I prefer?", top_k=5)
        ids = [r.item.id for r in results]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any("coffee" in r.item.content for r in results))

    def test_embed_cache_is_isolated_per_embedder(self) -> None:
        """Different embedders must not share cached vectors (regression)."""
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "I bought a red bicycle.",
            kind=MemoryKind.EPISODIC,
            source=source,
        )
        first = _TaggedEmbedder("first")
        second = _TaggedEmbedder("second")
        engine.recall("red bicycle", top_k=1, embedder=first)
        engine.recall("red bicycle", top_k=1, embedder=second)
        self.assertTrue(first.seen)
        self.assertTrue(second.seen)
        self.assertTrue(any("bicycle" in text for text in first.seen))
        self.assertTrue(any("bicycle" in text for text in second.seen))

    def test_dense_full_scan_is_skipped_above_threshold(self) -> None:
        """Without a vector index, huge stores must not embed everything."""
        embedder = _CountingEmbedder()
        results = _dense_results(
            _FakeEngine(), "some query", None, embedder, top_k=5
        )
        self.assertEqual(results, [])
        self.assertEqual(embedder.calls, 0)


if __name__ == "__main__":
    unittest.main()
