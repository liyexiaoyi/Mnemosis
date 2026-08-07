"""Sleep consolidation.

Human principle #1: while offline, the system replays experience and moves
repeated/important episodes into stable semantic knowledge, prunes noise, and
reconciles contradictions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable

from .backend import Backend
from .dual_track import DualTrackStore
from .types import MemoryItem, MemoryKind, MemoryStatus, hash_content, utcnow


@dataclass(slots=True)
class Conflict:
    """Two confident facts that both seem true but cannot be."""

    a: MemoryItem
    b: MemoryItem
    reason: str


@dataclass(slots=True)
class ConsolidationReport:
    promoted: list[MemoryItem] = field(default_factory=list)
    recycled: list[str] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    reflected: list[MemoryItem] = field(default_factory=list)
    replayed: int = 0
    merged: int = 0
    total_before: int = 0
    total_after: int = 0

    def summary(self) -> str:
        return (
            f"promoted {len(self.promoted)}, pruned {len(self.recycled)}, "
            f"reflected {len(self.reflected)}, replayed {self.replayed}, "
            f"merged {self.merged}, "
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
        llm_summarizer: Callable[[list[str]], str] | None = None,
        replay_window: int = 64,
        replay_min_importance: float = 0.4,
        replay_recency_days: float = 7.0,
    ) -> None:
        self.store = store
        self.backend = backend
        self.promotion_accesses = promotion_accesses
        self.promotion_age_hours = promotion_age_hours
        self.promotion_importance = promotion_importance
        self.prune_importance = prune_importance
        self.prune_age_days = prune_age_days
        self.conflict_min_confidence = conflict_min_confidence
        self.llm_summarizer = llm_summarizer
        self.replay_window = max(1, int(replay_window))
        self.replay_min_importance = replay_min_importance
        self.replay_recency_days = max(1.0, replay_recency_days)

    def sleep(
        self,
        now: datetime | None = None,
        summarizer: Callable[[list[str]], str] | None = None,
    ) -> ConsolidationReport:
        now = now or utcnow()
        total_before = len(self.store.all_active())
        replayed = self._replay_recent(now)
        merged = self._merge_duplicates(now)
        promoted = self._promote_episodic(now)
        recycled = self._prune_noise(now)
        conflicts = self.detect_conflicts()
        reflected = self.reflect(summarizer or self.llm_summarizer, now)
        total_after = len(self.store.all_active())
        return ConsolidationReport(
            promoted=promoted,
            recycled=recycled,
            conflicts=conflicts,
            reflected=reflected,
            replayed=replayed,
            merged=merged,
            total_before=total_before,
            total_after=total_after,
        )

    def _merge_duplicates(self, now: datetime) -> int:
        """Merge near-duplicate episodic traces (complementary learning
        systems; McClelland et al., 1995).

        Repeated experiences that are lexically near-identical (e.g. the same
        event logged twice from different sources) collapse into one trace
        with an evidence count, instead of polluting recall with copies. Only
        same-content-hash episodes are considered, so distinct events are
        never fused.
        """
        episodes = self.store.all_active(MemoryKind.EPISODIC)
        by_hash: dict[str, list[MemoryItem]] = {}
        for item in episodes:
            by_hash.setdefault(item.content_hash, []).append(item)
        merged = 0
        for _hash, items in by_hash.items():
            if len(items) < 2:
                continue
            items.sort(key=lambda i: (i.seq, i.id))
            keep = items[0]
            keep.evidence_count = max(
                keep.evidence_count, sum(i.evidence_count for i in items)
            )
            keep.importance = max(i.importance for i in items)
            keep.confidence = min(1.0, keep.confidence + 0.05 * (len(items) - 1))
            self.backend.update(keep)
            for dup in items[1:]:
                dup.status = MemoryStatus.RECYCLED
                self.backend.update(dup)
                merged += 1
        return merged

    def _replay_recent(self, now: datetime) -> int:
        """Offline replay of recent salient traces (Gais et al., 2002;
        Rasch & Born, 2013).

        Sleep spindles preferentially replay traces encoded during the most
        recent waking period, and emotional/salient content is replayed more
        often. We emulate this with a bounded replay pass over the newest
        episodic memories: each gets a small durable storage-strength gain
        that scales with recency and importance. The window is bounded so the
        pass stays cheap at scale.
        """
        episodes = self.store.all_active(MemoryKind.EPISODIC)
        episodes.sort(key=lambda item: item.seq, reverse=True)
        replay_window_seconds = self.replay_recency_days * 86400.0
        replayed = 0
        for item in episodes[: self.replay_window]:
            age_seconds = max(0.0, (now - item.created_at).total_seconds())
            if age_seconds > replay_window_seconds:
                continue
            if item.importance < self.replay_min_importance:
                continue
            recency_weight = 1.0 - 0.5 * min(1.0, age_seconds / replay_window_seconds)
            gain = 0.02 * recency_weight * (0.5 + item.importance)
            item.storage_strength = min(2.0, item.storage_strength + gain)
            item.strength = min(1.0, item.strength + gain)
            item.touch(now)
            self.backend.update(item)
            replayed += 1
        return replayed

    def reflect(
        self,
        summarizer: Callable[[list[str]], str] | None,
        now: datetime | None = None,
    ) -> list[MemoryItem]:
        """Reflection over supporting episodes (Park et al., 2023).

        Semantic facts backed by >= 2 linked episodes are re-written as an
        abstraction of those episodes. Without a summarizer this is a no-op.
        """
        if summarizer is None:
            return []
        now = now or utcnow()
        reflected: list[MemoryItem] = []
        for semantic in self.store.all_active(MemoryKind.SEMANTIC):
            if semantic.evidence_count < 2:
                continue
            episodes = [
                item
                for item in self.backend.related(
                    semantic.id, depth=1, max_nodes=20
                )
                if item.kind is MemoryKind.EPISODIC
                and item.status is MemoryStatus.ACTIVE
            ]
            if len(episodes) < 2:
                continue
            episodes.sort(key=lambda e: (e.created_at, e.content))
            try:
                summary = (summarizer([e.content for e in episodes]) or "").strip()
            except Exception:
                continue
            if not summary or summary == semantic.content:
                continue
            semantic.content = summary
            semantic.content_hash = hash_content(summary)
            semantic.updated_at = now
            self.backend.update(semantic)
            reflected.append(semantic)
        return reflected

    def _promote_episodic(self, now: datetime) -> list[MemoryItem]:
        promoted: list[MemoryItem] = []
        for item in self.store.all_active(MemoryKind.EPISODIC):
            # Rasch & Born (2013): sleep preferentially consolidates salient
            # (here: emotionally tagged) experiences.
            access_needed = max(
                1, self.promotion_accesses - (1 if item.affect else 0)
            )
            age_needed = self.promotion_age_hours * (0.5 if item.affect else 1.0)
            age_hours = (now - item.created_at).total_seconds() / 3600.0
            if item.access_count < access_needed:
                continue
            if age_hours < age_needed:
                continue
            if item.importance < self.promotion_importance and item.access_count < 3:
                continue
            # Complementary learning systems (McClelland et al., 1995):
            # semantic knowledge accumulates evidence from repeated episodes.
            existing = self.backend.find_by_hash(
                MemoryKind.SEMANTIC, hash_content(item.content)
            )
            evidence = (
                existing.evidence_count + item.evidence_count
                if existing
                else item.evidence_count
            )
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
                storage_strength=item.storage_strength,
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
