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
        suppression_factor: float = 0.02,
    ) -> list[RecallResult]:
        now = now or utcnow()
        candidates = self.backend.list(kind=kind)
        query_terms = set(tokenize(query))
        scored: list[RecallResult] = []
        for item in candidates:
            overlap = _overlap(query_terms, item)
            retrievability = self.curve.retrievability(item, now)
            context_match = (
                context is not None
                and item.context is not None
                and item.context.lower() == context.strip().lower()
            )
            score = (
                0.40 * overlap
                + 0.25 * retrievability
                + 0.20 * item.importance
                + (0.15 if context_match else 0.0)
            )
            reasons: list[str] = []
            if overlap > 0:
                reasons.append(f"cue/keyword overlap {overlap:.2f}")
            if retrievability < 0.5:
                reasons.append("partially forgotten")
            if item.importance >= 0.7:
                reasons.append("high importance")
            if context_match:
                reasons.append("context match")
            scored.append(RecallResult(item=item, score=score, reasons=reasons))
        scored.sort(key=lambda r: r.score, reverse=True)
        results = scored[:top_k]
        if reinforce:
            for r in results:
                # Testing effect (Roediger & Karpicke, 2006): reinforcement
                # scales with how well the memory matched the retrieval.
                overlap = _overlap(query_terms, r.item)
                delta = 0.05 + 0.15 * overlap
                self.curve.reinforce(r.item, delta=delta, now=now)
                self.backend.update(r.item)
            if suppression_factor > 0:
                self._suppress_linked_rivals(results, suppression_factor)
        return results

    def _suppress_linked_rivals(
        self,
        results: list[RecallResult],
        suppression_factor: float,
    ) -> None:
        """Retrieval-induced forgetting (Anderson, Bjork & Bjork, 1994).

        Memories linked to what was just recalled — but not themselves
        recalled — lose a little strength.
        """
        selected = {r.item.id for r in results}
        suppressed: set[str] = set()
        for r in results:
            for linked in self.backend.related(r.item.id, depth=1, max_nodes=50):
                if linked.id in selected or linked.id in suppressed:
                    continue
                linked.strength = max(0.0, linked.strength - suppression_factor)
                self.backend.update(linked)
                suppressed.add(linked.id)

    def recent(
        self, kind: MemoryKind | None = None, limit: int = 10
    ) -> list[MemoryItem]:
        return self.backend.list(kind=kind, limit=limit)

    def all_active(self, kind: MemoryKind | None = None) -> list[MemoryItem]:
        return self.backend.list(kind=kind)


def _overlap(query_terms: set[str], item: MemoryItem) -> float:
    """Keyword/cue overlap in [0, 1] between query and a memory."""
    item_terms = set(tokenize(item.content)) | set(item.cues)
    if not query_terms or not item_terms:
        return 0.0
    hits = len(query_terms & item_terms)
    return hits / max(1.0, math.sqrt(len(query_terms) * max(len(item_terms), 1)))


__all__ = ["DualTrackStore"]
