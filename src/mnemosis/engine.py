"""Mnemosis public facade."""

from __future__ import annotations

from datetime import datetime

from .association import AssociationIndex
from .backend import Backend, make_backend
from .consolidation import ConsolidationReport, Consolidator
from .dual_track import DualTrackStore
from .forgetting import ForgettingCurve, ReviewScheduler
from .importance import ImportanceScorer
from .metacognition import ConfidenceLabel, Metacognition, MetacognitiveCheck
from .recycle import RecycleBin
from .types import MemoryItem, MemoryKind, RecallResult, SourceRecord, SourceType


class MemoryEngine:
    """The one thing most users touch.

    ```python
    engine = MemoryEngine("memory.db")   # persistent
    engine = MemoryEngine()              # in-memory
    engine.remember(...)
    engine.recall(...)
    engine.sleep()
    engine.check(...)
    ```
    """

    def __init__(
        self,
        memory_file: str | None = None,
        *,
        decay_rate: float = 0.002,
        base_interval_hours: float = 24.0,
        importance_scorer: ImportanceScorer | None = None,
    ) -> None:
        self.backend: Backend = make_backend(memory_file)
        self.curve = ForgettingCurve(decay_rate)
        self.scheduler = ReviewScheduler(self.curve, base_interval_hours)
        self.scorer = importance_scorer or ImportanceScorer()
        self.store = DualTrackStore(self.backend, self.curve, self.scorer)
        self.associations = AssociationIndex(self.backend)
        self.consolidator = Consolidator(self.store, self.backend)
        self.meta = Metacognition(self.store, self.curve, self.consolidator)
        self.recycle = RecycleBin(self.backend)

    # -- wake cycle ---------------------------------------------------------

    def remember(
        self,
        content: str,
        *,
        kind: MemoryKind = MemoryKind.EPISODIC,
        source: SourceRecord | None = None,
        cues: list[str] | None = None,
        importance: float | None = None,
        confidence: float = 1.0,
        strength: float = 1.0,
        created_at: datetime | None = None,
    ) -> MemoryItem:
        source = source or SourceRecord(origin=SourceType.USER)
        item = self.store.remember(
            content,
            kind,
            source,
            cues=cues,
            importance=importance,
            confidence=confidence,
            strength=strength,
            created_at=created_at,
        )
        self.associations.index(item)
        self.associations.link_related(item)
        return item

    def recall(
        self,
        query: str,
        *,
        kind: MemoryKind | None = None,
        top_k: int = 5,
        now: datetime | None = None,
    ) -> list[RecallResult]:
        return self.store.recall(query, kind=kind, top_k=top_k, now=now)

    # -- sleep cycle ----------------------------------------------------------

    def sleep(self, now: datetime | None = None) -> ConsolidationReport:
        return self.consolidator.sleep(now)

    # -- active forgetting ----------------------------------------------------

    def forget(self, memory_id: str) -> bool:
        return self.recycle.trash(memory_id)

    def restore(self, memory_id: str) -> bool:
        return self.recycle.restore(memory_id)

    def purge(self, before: datetime | None = None, limit: int = 1000) -> int:
        return self.recycle.purge(before=before, limit=limit)

    def review_due(
        self, limit: int = 10, now: datetime | None = None
    ) -> list[MemoryItem]:
        return self.scheduler.due_items(self.store.all_active(), now=now, limit=limit)

    # -- metacognition ----------------------------------------------------------

    def check(
        self, query: str, top_k: int = 3, now: datetime | None = None
    ) -> MetacognitiveCheck:
        return self.meta.check(query, top_k=top_k, now=now)

    def confidence(
        self, item: MemoryItem, now: datetime | None = None
    ) -> tuple[ConfidenceLabel, float]:
        return self.meta.confidence(item, now)

    # -- associations -------------------------------------------------------------

    def related(self, memory_id: str, depth: int = 1, max_nodes: int = 20) -> list[MemoryItem]:
        return self.associations.related(memory_id, depth=depth, max_nodes=max_nodes)

    # -- misc ------------------------------------------------------------------------

    def stats(self) -> dict:
        stats = self.backend.stats()
        stats["trash"] = len(self.recycle.list_trash())
        stats["review_due"] = len(self.review_due(limit=1000))
        return stats

    def close(self) -> None:
        if hasattr(self.backend, "close"):
            self.backend.close()


__all__ = ["MemoryEngine"]

