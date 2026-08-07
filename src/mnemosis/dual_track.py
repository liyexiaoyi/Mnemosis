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
    ) -> list[RecallResult]:
        now = now or utcnow()
        candidates = self.backend.list(kind=kind)
        query_terms = set(tokenize(query))
        scored: list[RecallResult] = []
        for item in candidates:
            overlap = _overlap(query_terms, item)
            retrievability = self.curve.retrievability(item, now)
            score = 0.45 * overlap + 0.30 * retrievability + 0.25 * item.importance
            reasons: list[str] = []
            if overlap > 0:
                reasons.append(f"cue/keyword overlap {overlap:.2f}")
            if retrievability < 0.5:
                reasons.append("partially forgotten")
            if item.importance >= 0.7:
                reasons.append("high importance")
            scored.append(RecallResult(item=item, score=score, reasons=reasons))
        scored.sort(key=lambda r: r.score, reverse=True)
        results = scored[:top_k]
        if reinforce:
            for r in results:
                self.curve.reinforce(r.item, now=now)
                self.backend.update(r.item)
        return results

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

