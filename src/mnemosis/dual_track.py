"""Dual-track memory: episodic ("what happened") vs semantic ("what is true").

Human principle #4. Events keep their narrative and time; facts are
deduplicated and kept stable. Recall paths are separate per track.
"""

from __future__ import annotations

import math
from datetime import datetime

from .backend import Backend
from .forgetting import ForgettingCurve
from .importance import ImportanceScorer
from .embedding import Embedder
from .types import (
    MemoryItem,
    MemoryKind,
    RecallResult,
    SourceRecord,
    normalize_cues,
    tokenize,
    utcnow,
)


class DualTrackStore:
    def __init__(
        self,
        backend: Backend,
        curve: ForgettingCurve,
        scorer: ImportanceScorer,
    ) -> None:
        self.backend = backend
        self.curve = curve
        self.scorer = scorer
        self._term_cache: dict[tuple, frozenset[str]] = {}
        self._embed_cache: dict[str, list[float]] = {}

    def remember(
        self,
        content: str,
        kind: MemoryKind,
        source: SourceRecord,
        *,
        cues: list[str] | None = None,
        importance: float | None = None,
        confidence: float = 1.0,
        strength: float = 1.0,
        created_at: datetime | None = None,
        context: str | None = None,
        affect: str | None = None,
        evidence_count: int = 1,
        storage_strength: float = 1.0,
    ) -> MemoryItem:
        if importance is None:
            importance = self.scorer.score(content, source=source)
        item = MemoryItem(
            content=content,
            kind=kind,
            source=source,
            cues=normalize_cues(cues or []),
            created_at=created_at or utcnow(),
            importance=importance,
            confidence=confidence,
            strength=strength,
            context=context,
            affect=affect,
            evidence_count=evidence_count,
            storage_strength=storage_strength,
        )
        if kind is MemoryKind.SEMANTIC:
            stored = self.backend.upsert(item)
        else:
            self.backend.add(item)
            stored = item
        self.backend.add_cues(stored.id, stored.cues)
        return stored

    def recall(
        self,
        query: str,
        *,
        kind: MemoryKind | None = None,
        top_k: int = 5,
        now: datetime | None = None,
        reinforce: bool = True,
        context: str | None = None,
        suppression_factor: float = 0.01,
        suppression_min_cues: int = 2,
        suppression_floor: float = 0.7,
        embedder: Embedder | None = None,
        expansion_discount: float = 0.95,
        max_expansion_roots: int = 5,
        max_expansion_neighbors: int = 50,
    ) -> list[RecallResult]:
        now = now or utcnow()
        candidates = self.backend.list(kind=kind)
        query_terms = set(tokenize(query))
        query_vector = embedder.embed(query) if embedder is not None else None
        scored: list[tuple[float, float, MemoryItem, list[str], bool]] = []
        for item in candidates:
            overlap = _overlap(query_terms, self._terms(item))
            retrievability = min(
                1.0, self.curve.retrievability(item, now)
            )
            context_match = (
                context is not None
                and item.context is not None
                and item.context.lower() == context.strip().lower()
            )
            reasons: list[str] = []
            semantic = 0.0
            if query_vector is not None:
                item_vector = self._embedding(item, embedder)
                semantic = embedder.cosine(query_vector, item_vector)
                score = (
                    0.30 * overlap
                    + 0.20 * retrievability
                    + 0.15 * item.importance
                    + (0.15 if context_match else 0.0)
                    + 0.20 * semantic
                )
            else:
                score = (
                    0.40 * overlap
                    + 0.25 * retrievability
                    + 0.20 * item.importance
                    + (0.15 if context_match else 0.0)
                )
            if overlap > 0:
                reasons.append(f"cue/keyword overlap {overlap:.2f}")
            if semantic > 0.5:
                reasons.append(f"semantic similarity {semantic:.2f}")
            if retrievability < 0.5:
                reasons.append("partially forgotten")
            if item.importance >= 0.7:
                reasons.append("high importance")
            if context_match:
                reasons.append("context match")
            matched = overlap > 0.0 or semantic >= 0.2
            scored.append((score, overlap, item, reasons, matched))
        scored.sort(key=lambda entry: entry[0], reverse=True)
        self._spread_activation(
            scored,
            query_terms,
            now,
            context,
            query_vector,
            embedder,
            expansion_discount,
            max_expansion_roots,
            max_expansion_neighbors,
        )
        results = [
            RecallResult(item=item, score=score, reasons=reasons)
            for score, _, item, reasons, _ in scored[:top_k]
        ]
        if reinforce:
            for score, overlap, item, _, matched in scored[:top_k]:
                if not matched:
                    continue  # failed retrieval does not strengthen (testing effect)
                # Testing effect (Roediger & Karpicke, 2006): reinforcement
                # scales with how well the memory matched the retrieval.
                delta = 0.05 + 0.15 * overlap
                self.curve.reinforce(item, delta=delta, now=now)
                self.backend.update(item)
            if suppression_factor > 0:
                matched_items = [
                    item
                    for _, _, item, _, matched in scored[:top_k]
                    if matched
                ]
                self._suppress_linked_rivals(
                    matched_items,
                    suppression_factor,
                    suppression_min_cues,
                    suppression_floor,
                    query_terms,
                )
        return results

    def _terms(self, item: MemoryItem) -> frozenset[str]:
        """Cached token terms for an item (auto-invalidated on change)."""
        key = (item.id, item.content_hash, item.revision_count, tuple(item.cues))
        cached = self._term_cache.get(key)
        if cached is None:
            cached = frozenset(tokenize(item.content)) | frozenset(item.cues)
            self._term_cache[key] = cached
        return cached

    def _embedding(self, item: MemoryItem, embedder: Embedder) -> list[float]:
        """Cached embedding for an item (keyed by content hash)."""
        cached = self._embed_cache.get(item.content_hash)
        if cached is None:
            cached = embedder.embed(item.content)
            self._embed_cache[item.content_hash] = cached
        return cached

    def _spread_activation(
        self,
        scored: list[tuple[float, float, MemoryItem, list[str], bool]],
        query_terms: set[str],
        now: datetime,
        context: str | None,
        query_vector: list[float] | None,
        embedder: Embedder | None,
        discount: float,
        max_roots: int,
        max_neighbors: int,
    ) -> None:
        """Spreading activation over the association graph (HippoRAG-style).

        Memories linked to the strongest matches get a discounted score boost,
        so "what did Alice do after X?" can surface the chronologically next
        event even when it shares no words with the query.
        """
        roots = [entry for entry in scored[:max_roots] if entry[4]]
        if not roots:
            return
        activated: dict[str, tuple[float, MemoryItem]] = {}
        for root_score, _, root, _, _ in roots:
            neighbors = self.backend.related(
                root.id, depth=1, max_nodes=1000
            )
            # Temporal contiguity: temporally adjacent memories associate more
            # strongly, so their activation decays with distance from the root.
            neighbors.sort(
                key=lambda item: abs(
                    (item.created_at - root.created_at).total_seconds()
                )
            )
            for rank, linked in enumerate(neighbors[:max_neighbors]):
                boost = root_score * discount * (0.985**rank)
                current = activated.get(linked.id)
                if current is None or boost > current[0]:
                    activated[linked.id] = (boost, root)
        if not activated:
            return

        activated_ids = set(activated)
        for index, (score, overlap, item, reasons, matched) in enumerate(scored):
            if item.id not in activated_ids:
                continue
            boost, root = activated[item.id]
            if boost > score:
                reason = f"linked to '{root.content[:40]}'"
                scored[index] = (boost, overlap, item, reasons + [reason], matched)
        for linked_id, (boost, root) in activated.items():
            if any(entry[2].id == linked_id for entry in scored):
                continue
            linked = self.backend.get(linked_id)
            if linked is None:
                continue
            scored.append(
                (
                    boost,
                    0.0,
                    linked,
                    [f"linked to '{root.content[:40]}'"],
                    False,
                )
            )
        scored.sort(key=lambda entry: entry[0], reverse=True)

    def _suppress_linked_rivals(
        self,
        items: list[MemoryItem],
        suppression_factor: float,
        min_shared_cues: int,
        floor: float,
        query_terms: set[str],
    ) -> None:
        """Retrieval-induced forgetting (Anderson, Bjork & Bjork, 1994).

        Only *close competitors* — linked memories sharing at least
        `min_shared_cues` cues with what was recalled — lose a little
        strength. This mirrors RIF's category-competitor effect instead of
        punishing everything loosely related.
        """
        selected = {item.id for item in items}
        suppressed: set[str] = set()
        for item in items:
            item_cues = set(item.cues)
            for linked in self.backend.related(item.id, depth=1, max_nodes=50):
                if linked.id in selected or linked.id in suppressed:
                    continue
                if len(item_cues & set(linked.cues)) < min_shared_cues:
                    continue
                if not _overlap(query_terms, self._terms(linked)) > 0.0:
                    continue  # only true retrieval competitors are suppressed
                linked.strength = max(
                    floor, linked.strength - suppression_factor
                )
                self.backend.update(linked)
                suppressed.add(linked.id)

    def recent(
        self, kind: MemoryKind | None = None, limit: int = 10
    ) -> list[MemoryItem]:
        return self.backend.list(kind=kind, limit=limit)

    def all_active(self, kind: MemoryKind | None = None) -> list[MemoryItem]:
        return self.backend.list(kind=kind)


def _overlap(query_terms: set[str], item_terms: frozenset[str]) -> float:
    """Keyword/cue overlap in [0, 1] between query and an item's terms."""
    if not query_terms or not item_terms:
        return 0.0
    hits = len(query_terms & item_terms)
    return hits / max(
        1.0, math.sqrt(len(query_terms) * max(len(item_terms), 1))
    )


__all__ = ["DualTrackStore"]
