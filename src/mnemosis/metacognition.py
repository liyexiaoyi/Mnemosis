"""Metacognition: confidence, contradictions, knowledge gaps.

Human principle #8: humans doubt themselves, ask for confirmation, and notice
when they do not know. This module turns that into an API.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .consolidation import Conflict
from .dual_track import DualTrackStore
from .forgetting import ForgettingCurve
from .types import MemoryItem, SourceType, tokenize, utcnow


class ConfidenceLabel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(slots=True)
class MetacognitiveCheck:
    """Result of `engine.check(query)`: think before answering."""

    query: str
    items: list[tuple[MemoryItem, ConfidenceLabel, float]] = field(default_factory=list)
    contradictions: list[Conflict] = field(default_factory=list)
    gaps: list[str] = field(default_factory=list)
    blocked: list[MemoryItem] = field(default_factory=list)

    def should_confirm_any(self) -> bool:
        return any(label is ConfidenceLabel.LOW for _, label, _ in self.items)


class Metacognition:
    def __init__(
        self,
        store: DualTrackStore,
        curve: ForgettingCurve,
        consolidator=None,
    ) -> None:
        self.store = store
        self.curve = curve
        self.consolidator = consolidator

    def confidence(
        self, item: MemoryItem, now: datetime | None = None
    ) -> tuple[ConfidenceLabel, float]:
        now = now or utcnow()
        retrievability = self.curve.retrievability(item, now)
        value = (
            item.confidence
            * (0.45 + 0.55 * retrievability)
            * (0.8 + 0.2 * min(item.access_count, 3) / 3.0)
            * (0.95 + 0.05 * min(item.evidence_count, 5) / 5.0)
        )
        value = max(0.0, min(1.0, value))
        if value >= 0.7:
            return ConfidenceLabel.HIGH, round(value, 3)
        if value >= 0.4:
            return ConfidenceLabel.MEDIUM, round(value, 3)
        return ConfidenceLabel.LOW, round(value, 3)

    def contradictions(self) -> list[Conflict]:
        if self.consolidator is None:
            return []
        return self.consolidator.detect_conflicts()

    def knowledge_gaps(self, query: str, top_k: int = 8) -> list[str]:
        """Query terms that no active memory can account for."""
        query_terms = set(tokenize(query))
        known: set[str] = set()
        for item in self.store.all_active():
            known |= set(tokenize(item.content))
            known |= set(item.cues)
        return [term for term in sorted(query_terms) if term not in known][:top_k]

    def blocked_retrievals(
        self, query: str, top_k: int = 3, now: datetime | None = None
    ) -> list[MemoryItem]:
        """Schacter's "blocking" sin: cues match, but the memory was not recalled.

        These are candidate memories that share cues with the query yet fell
        outside the top-k results — a feeling-of-knowing signal that the agent
        should try alternative retrieval routes instead of giving up.
        """
        query_terms = set(tokenize(query))
        results = self.store.recall(query, top_k=top_k, now=now)
        recalled = {r.item.id for r in results}
        return [
            item
            for item in self.store.all_active()
            if item.id not in recalled and set(item.cues) & query_terms
        ]

    def should_confirm(self, item: MemoryItem, now: datetime | None = None) -> bool:
        """Signal that the agent should double-check before asserting."""
        label, _ = self.confidence(item, now)
        if label is ConfidenceLabel.LOW:
            return True
        return item.source.origin is SourceType.INFERENCE and item.confidence < 0.8

    def check(
        self, query: str, top_k: int = 3, now: datetime | None = None
    ) -> MetacognitiveCheck:
        now = now or utcnow()
        results = self.store.recall(query, top_k=top_k, now=now)
        items = [(r.item, *self.confidence(r.item, now)) for r in results]
        return MetacognitiveCheck(
            query=query,
            items=items,
            contradictions=self.contradictions(),
            gaps=self.knowledge_gaps(query),
            blocked=self.blocked_retrievals(query, top_k, now),
        )


__all__ = ["ConfidenceLabel", "Metacognition", "MetacognitiveCheck"]
