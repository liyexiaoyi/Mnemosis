"""Sleep consolidation.

Human principle #1: while offline, the system replays experience and moves
repeated/important episodes into stable semantic knowledge, prunes noise, and
reconciles contradictions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from .backend import Backend
from .dual_track import DualTrackStore
from .types import MemoryItem, MemoryKind, MemoryStatus, hash_content, utcnow


@dataclass
class Conflict:
    """Two confident facts that both seem true but cannot be."""

    a: MemoryItem
    b: MemoryItem
    reason: str


@dataclass
class ConsolidationReport:
    promoted: list[MemoryItem] = field(default_factory=list)
    recycled: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    total_before: int = 0
    total_after: int = 0

    def summary(self) -> str:
        return (
            f"promoted {len(self.promoted)}, pruned {len(self.recycled)}, "
            f"conflicts {len(self.conflicts)} "
            f"({self.total_before} -> {self.total_after} active memories)"
        )


class Consolidator:
    def __init__(
        self,
        store: DualTrackStore,
        backend: Backend,
        *,
        promotion_accesses: int = 2,
        promotion_age_hours: float = 24.0,
        promotion_importance: float = 0.6,
        prune_importance: float = 0.2,
        prune_age_days: float = 30.0,
        conflict_min_confidence: float = 0.6,
    ) -> None:
        self.store = store
        self.backend = backend
        self.promotion_accesses = promotion_accesses
        self.promotion_age_hours = promotion_age_hours
        self.promotion_importance = promotion_importance
        self.prune_importance = prune_importance
        self.prune_age_days = prune_age_days
        self.conflict_min_confidence = conflict_min_confidence

    def sleep(self, now: datetime | None = None) -> ConsolidationReport:
        now = now or utcnow()
        total_before = len(self.store.all_active())
        promoted = self._promote_episodic(now)
        recycled = self._prune_noise(now)
        conflicts = self.detect_conflicts()
        total_after = len(self.store.all_active())
        return ConsolidationReport(
            promoted=promoted,
            recycled=recycled,
            conflicts=conflicts,
            total_before=total_before,
            total_after=total_after,
        )

    def _promote_episodic(self, now: datetime) -> list[MemoryItem]:
        promoted: list[MemoryItem] = []
        for item in self.store.all_active(MemoryKind.EPISODIC):
            age_hours = (now - item.created_at).total_seconds() / 3600.0
            if item.access_count < self.promotion_accesses:
                continue
            if age_hours < self.promotion_age_hours:
                continue
            if item.importance < self.promotion_importance and item.access_count < 3:
                continue
            # Complementary learning systems (McClelland et al., 1995):
            # semantic knowledge accumulates evidence from repeated episodes.
            existing = self.backend.find_by_hash(
                MemoryKind.SEMANTIC, hash_content(item.content)
            )
            evidence = existing.evidence_count + 1 if existing else 1
            semantic = self.store.remember(
                item.content,
                MemoryKind.SEMANTIC,
                source=item.source,
                cues=list(item.cues) + ["consolidated"],
                importance=max(item.importance, self.promotion_importance),
                confidence=min(1.0, 0.6 + 0.08 * evidence),
                strength=item.strength,
                context=item.context,
                affect=item.affect,
                evidence_count=evidence,
            )
            self.backend.add_link(item.id, semantic.id)
            self.backend.add_link(semantic.id, item.id)
            promoted.append(semantic)
        return promoted

    def _prune_noise(self, now: datetime) -> list[str]:
        recycled: list[str] = []
        for item in self.store.all_active(MemoryKind.EPISODIC):
            age_days = (now - item.created_at).total_seconds() / 86400.0
            if (
                item.importance < self.prune_importance
                and item.access_count == 0
                and age_days >= self.prune_age_days
            ):
                item.status = MemoryStatus.RECYCLED
                self.backend.update(item)
                recycled.append(item.id)
        return recycled

    def detect_conflicts(self) -> list[Conflict]:
        """Heuristic: confident semantic memories sharing a cue but differing."""
        semantic = [
            item
            for item in self.store.all_active(MemoryKind.SEMANTIC)
            if item.confidence >= self.conflict_min_confidence
        ]
        groups: dict[str, list[MemoryItem]] = {}
        for item in semantic:
            for cue in item.cues:
                groups.setdefault(cue, []).append(item)

        conflicts: list[Conflict] = []
        seen_pairs: set[frozenset[str]] = set()
        for cue, items in groups.items():
            for i in range(len(items)):
                for j in range(i + 1, len(items)):
                    a, b = items[i], items[j]
                    if a.content_hash == b.content_hash:
                        continue
                    pair = frozenset({a.id, b.id})
                    if pair in seen_pairs:
                        continue
                    seen_pairs.add(pair)
                    conflicts.append(
                        Conflict(
                            a=a,
                            b=b,
                            reason=f"confident facts share cue '{cue}' but differ",
                        )
                    )
        return conflicts


__all__ = ["Conflict", "ConsolidationReport", "Consolidator"]
