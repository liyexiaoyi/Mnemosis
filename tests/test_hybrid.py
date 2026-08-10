"""Tests for fused multi-path retrieval (hybrid.py)."""

from __future__ import annotations

from mnemosis import MemoryEngine
from mnemosis.hybrid import (
    english_inflections,
    rrf_scores,
    temporal_intent,
)
from mnemosis.embedding import Embedder
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


def test_english_inflections() -> None:
    expanded = english_inflections({"followers", "experienced", "weeks", "car"})
    assert "follower" in expanded
    assert "experience" in expanded
    assert "week" in expanded
    assert "car" in expanded


def test_temporal_intent() -> None:
    assert temporal_intent("What was the first issue I had?")["direction"] == "oldest"
    assert temporal_intent("What is my current address?")["direction"] == "newest"
    hints = temporal_intent("What happened after 2023/04/10?")
    assert hints["direction"] == "newest"
    assert hints["after"].year == 2023
    # "may" as a modal verb must not be treated as the month of May.
    assert "month" not in temporal_intent("I may go to the store")
    assert temporal_intent("I visited in May 5")["month"] == 5


def test_rrf_ranks_shared_winners_first() -> None:
    fused = rrf_scores(
        [["a", "b", "c"], ["a", "b", "c"]],
        k=60,
    )
    assert fused["a"] > fused["b"]
    assert fused["b"] > fused["c"]
    # A candidate ranked first by both passes beats one ranked first by one.
    fused2 = rrf_scores([["a", "b"], ["a", "b"]], k=60)
    fused3 = rrf_scores([["b", "a"], ["c", "a"]], k=60)
    assert fused2["a"] > fused3["a"]


def test_fused_recall_keeps_top_keyword_hit() -> None:
    engine = _engine_with(
        "I bought a red bicycle on March 5th and rode it to work.",
        "We discussed holiday plans for summer.",
        "The red bike got a flat tire last week.",
    )
    results = engine.recall_fused("What happened to my red bicycle?", top_k=2)
    contents = [r.item.content for r in results]
    assert any("bicycle" in c for c in contents)
    assert any("flat tire" in c for c in contents)


def test_fused_recall_dedupes() -> None:
    engine = _engine_with(
        "I prefer dark roast coffee with no sugar.",
        "My favorite movie is Interstellar.",
    )
    results = engine.recall_fused("What coffee do I prefer?", top_k=5)
    ids = [r.item.id for r in results]
    assert len(ids) == len(set(ids))
    assert any("coffee" in r.item.content for r in results)


class _TaggedEmbedder(Embedder):
    """Embedder that records every text it embeds."""

    def __init__(self, tag: str) -> None:
        self.tag = tag
        self.seen: list[str] = []

    def embed(self, text: str) -> list[float]:
        self.seen.append(text)
        return [1.0, 0.0]


def test_embed_cache_is_isolated_per_embedder() -> None:
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
    assert first.seen
    assert second.seen
    # Both embedders embedded the item content independently.
    assert any("bicycle" in text for text in first.seen)
    assert any("bicycle" in text for text in second.seen)
