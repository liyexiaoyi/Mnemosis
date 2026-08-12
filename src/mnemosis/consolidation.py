"""Sleep consolidation.

Human principle #1: while offline, the system replays experience and moves
repeated/important episodes into stable semantic knowledge, prunes noise, and
reconciles contradictions.
"""

from __future__ import annotations

import logging
from collections import Counter
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime

from .backend import Backend
from .dual_track import DualTrackStore
from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    hash_content,
    tokenize,
    utcnow,
)

_LOG = logging.getLogger(__name__)

_MAX_CUE_GROUP = 120
"""Strongest items compared per shared cue during sleep/conflict scans."""

_MAX_PAIRS_PER_CUE = 1000
"""Pairwise budget per cue so sleep stays O(N) worst-case on huge stores."""

_REM_CUE_BUCKET_LIMIT = 500
"""Max items kept per cue for REM association (over-generic cues skipped)."""

_REM_LINK_BUDGET = 200_000
"""Max association edges written per sleep (bounded repeat cost)."""


def _bounded_pairs(items: list[MemoryItem]) -> Iterator[tuple[MemoryItem, MemoryItem]]:
    """Yield at most ``_MAX_PAIRS_PER_CUE`` pairs from the strongest items.

    The strongest facts (highest confidence/importance) carry the most
    information for accommodation and conflict detection; truncating the
    weakest tail keeps large stores from exploding into O(N^2) work.
    """
    pool = sorted(
        items,
        key=lambda item: (item.confidence, item.importance, item.seq),
        reverse=True,
    )[:_MAX_CUE_GROUP]
    budget = _MAX_PAIRS_PER_CUE
    for i in range(len(pool)):
        for j in range(i + 1, len(pool)):
            if budget <= 0:
                return
            budget -= 1
            yield pool[i], pool[j]


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
    rem_links: int = 0
    rem_resolved: int = 0
    emotion_boosted: int = 0
    emotion_links: int = 0
    accommodated: int = 0
    weak_replayed: int = 0
    total_before: int = 0
    total_after: int = 0

    def summary(self) -> str:
        return (
            f"promoted {len(self.promoted)}, pruned {len(self.recycled)}, "
            f"reflected {len(self.reflected)}, replayed {self.replayed}, "
            f"merged {self.merged}, rem_links {self.rem_links}, "
            f"rem_resolved {self.rem_resolved}, "
            f"emotion_boosted {self.emotion_boosted}, "
            f"emotion_links {self.emotion_links}, "
            f"accommodated {self.accommodated}, "
            f"weak_replayed {self.weak_replayed}, "
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
        weak_replay_importance: float = 0.6,
        weak_replay_threshold: float = 0.35,
        weak_replay_max: int = 100,
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
        self.weak_replay_importance = weak_replay_importance
        self.weak_replay_threshold = weak_replay_threshold
        self.weak_replay_max = weak_replay_max

    def sleep(
        self,
        now: datetime | None = None,
        summarizer: Callable[[list[str]], str] | None = None,
    ) -> ConsolidationReport:
        now = now or utcnow()
        total_before = self.backend.count()
        replayed = self._replay_recent(now)
        # Load the episodic store once and share it across the phases that
        # scan it; each phase filters ACTIVE status in memory, which matches
        # the fresh-load semantics while avoiding ~5 full SQLite loads.
        episodes = self.store.all_active(MemoryKind.EPISODIC)
        merged = self._merge_duplicates(now, episodes)
        promoted = self._promote_episodic(now, episodes)
        recycled = self._prune_noise(now, episodes)
        # Semantic snapshot is loaded after promotion so the newly promoted
        # facts participate in conflict detection, accommodation and
        # reflection without three separate full-store loads.
        semantic_items = self.store.all_active(MemoryKind.SEMANTIC)
        # Weak replay runs on the post-promotion snapshot: after merge and
        # promotion the semantic store is final, so only one semantic load
        # is needed for the whole sleep cycle.
        weak_replayed = self._replay_weak_important(now, semantic_items)
        conflicts = self.detect_conflicts(semantic_items)
        rem_links, rem_resolved = self._rem_phase(now, conflicts, episodes)
        emotion_boosted, emotion_links = self._emotion_phase(now, episodes)
        accommodated = self._accommodation_phase(now, semantic_items)
        reflected = self.reflect(
            summarizer or self.llm_summarizer, now, semantic_items
        )
        total_after = self.backend.count()
        return ConsolidationReport(
            promoted=promoted,
            recycled=recycled,
            conflicts=conflicts,
            reflected=reflected,
            replayed=replayed,
            merged=merged,
            rem_links=rem_links,
            rem_resolved=rem_resolved,
            emotion_boosted=emotion_boosted,
            emotion_links=emotion_links,
            accommodated=accommodated,
            weak_replayed=weak_replayed,
            total_before=total_before,
            total_after=total_after,
        )

    def _replay_weak_important(
        self, now: datetime, semantic: list[MemoryItem] | None = None
    ) -> int:
        """Replay important-but-fading traces during sleep.

        Sleep-dependent consolidation prioritises salient content
        (Stickgold & Walker, 2013): a high-importance *consolidated
        semantic* trace that is about to fade gets a bounded durable gain
        even if it is old and outside the recency window. Episodes keep
        their existing recency-based replay contract; this protects
        important knowledge from silent forgetting.
        """
        candidates = [
            item
            for item in (
                semantic
                if semantic is not None
                else self.store.all_active(MemoryKind.SEMANTIC)
            )
            if item.kind is MemoryKind.SEMANTIC
            and item.importance >= self.weak_replay_importance
            and self.store.curve.retrievability(item, now)
            < self.weak_replay_threshold
        ]
        candidates.sort(
            key=lambda item: (item.importance, item.seq),
            reverse=True,
        )
        replayed = 0
        for item in candidates[: self.weak_replay_max]:
            gain = 0.03 * (0.5 + item.importance)
            item.storage_strength = min(2.0, item.storage_strength + gain)
            item.strength = min(1.0, item.strength + gain)
            item.touch(now)
            self.backend.update(item)
            replayed += 1
        return replayed

    def _accommodation_phase(
        self, now: datetime, semantic: list[MemoryItem] | None = None
    ) -> int:
        """Constructivist accommodation (Piaget via CAM; Li et al., 2025).

        New information either *assimilates* into an existing schema or forces
        the schema to *accommodate* (change). We emulate accommodation during
        sleep: when two confident facts share a cue but one is backed by at
        least 3x the evidence (and at least equal source trust), the weaker
        one is retired instead of lingering as a contradiction. Balanced
        disagreements are left to REM conflict-resolution instead.
        """
        semantic = [
            item
            for item in (
                semantic
                if semantic is not None
                else self.store.all_active(MemoryKind.SEMANTIC)
            )
            if item.status is MemoryStatus.ACTIVE
            and item.confidence >= 0.5
        ]
        groups: dict[str, list[MemoryItem]] = {}
        for item in semantic:
            for cue in item.cues:
                groups.setdefault(cue, []).append(item)
        accommodated = 0
        seen_pairs: set[frozenset[str]] = set()
        for items in groups.values():
            for a, b in _bounded_pairs(items):
                if a.content_hash == b.content_hash:
                    continue
                pair = frozenset({a.id, b.id})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                dominant, weaker = self._dominant(a, b)
                if dominant is None or weaker is None:
                    continue
                weaker.status = MemoryStatus.RECYCLED
                weaker.updated_at = now
                self.backend.update(weaker)
                accommodated += 1
        return accommodated

    @staticmethod
    def _dominant(
        a: MemoryItem, b: MemoryItem
    ) -> tuple[MemoryItem, MemoryItem] | tuple[None, None]:
        """Return (dominant, weaker) when evidence is clearly lopsided."""
        ea, eb = a.evidence_count, b.evidence_count
        ta, tb = a.source.trust, b.source.trust
        if ea >= 3 * eb and ta >= tb:
            return a, b
        if eb >= 3 * ea and tb >= ta:
            return b, a
        return None, None

    def _emotion_phase(
        self, now: datetime, episodes: list[MemoryItem] | None = None
    ) -> tuple[int, int]:
        """Amygdala-modulated consolidation (McGaugh, 2004; Krenz et al., 2025).

        Emotionally arousing experiences are consolidated more strongly than
        neutral ones, and *recurring* emotional events benefit most: the
        initial amygdala response stabilises a neocortical pattern that later
        repetitions strengthen (Krenz et al., 2025, J. Neurosci.). We emulate:

        - recurring emotional episodes (same content hash collapsed by the
          merge pass, so their `evidence_count` is the number of repeats)
          gain extra confidence / storage strength on top of plain merge;
        - links between distinct emotional episodes sharing a cue are
          strengthened (amygdala-hippocampal coupling), so one cue can
          re-activate the whole emotional cluster.
        """
        episodes = (
            episodes
            if episodes is not None
            else self.store.all_active(MemoryKind.EPISODIC)
        )
        emotional = [
            item
            for item in episodes
            if item.status is MemoryStatus.ACTIVE and item.affect
        ]
        boosted = 0
        for item in emotional:
            repeats = item.evidence_count
            if repeats < 2:
                continue
            gain = repeats - 1
            item.confidence = min(1.0, item.confidence + 0.03 * gain)
            item.storage_strength = min(
                2.0, item.storage_strength + 0.05 * gain
            )
            item.strength = min(1.0, item.strength + 0.03)
            self.backend.update(item)
            boosted += 1

        links = 0
        pending_links: list[tuple[str, str, float]] = []
        if len(emotional) >= 2:
            # Same cue-inverted pairing as the REM pass: only pairs that
            # share a cue are examined instead of every O(N^2) pair.
            cue_freq: dict[str, int] = {}
            for item in emotional:
                for cue in item.cues:
                    cue_freq[cue] = cue_freq.get(cue, 0) + 1
            cue_map: dict[str, list[MemoryItem]] = {}
            for item in emotional:
                for cue in item.cues:
                    if cue_freq.get(cue, 0) > _REM_CUE_BUCKET_LIMIT:
                        continue
                    bucket = cue_map.get(cue)
                    if bucket is None:
                        bucket = []
                        cue_map[cue] = bucket
                    if len(bucket) < _REM_CUE_BUCKET_LIMIT:
                        bucket.append(item)
            order = {item.id: index for index, item in enumerate(emotional)}
            cue_idx_map = {
                cue: [order[item.id] for item in bucket]
                for cue, bucket in cue_map.items()
            }
            counts: Counter[int] = Counter()
            for a_idx, a in enumerate(emotional):
                counts.clear()
                for cue in a.cues:
                    indices = cue_idx_map.get(cue)
                    if indices is not None:
                        counts.update(indices)
                for b_idx in counts:
                    if b_idx <= a_idx:
                        continue
                    b = emotional[b_idx]
                    if a.content_hash == b.content_hash:
                        continue
                    pending_links.append((a.id, b.id, 1.2))
                    pending_links.append((b.id, a.id, 1.2))
                    links += 1
        if pending_links:
            self.backend.add_links_many(pending_links)
        return boosted, links

    def _merge_duplicates(
        self, now: datetime, episodes: list[MemoryItem] | None = None
    ) -> int:
        """Merge near-duplicate episodic traces (complementary learning
        systems; McClelland et al., 1995).

        Repeated experiences that are lexically near-identical (e.g. the same
        event logged twice from different sources) collapse into one trace
        with an evidence count, instead of polluting recall with copies. Only
        same-content-hash episodes are considered, so distinct events are
        never fused.
        """
        episodes = (
            episodes
            if episodes is not None
            else self.store.all_active(MemoryKind.EPISODIC)
        )
        by_hash: dict[str, list[MemoryItem]] = {}
        for item in episodes:
            if item.status is not MemoryStatus.ACTIVE:
                continue
            by_hash.setdefault(item.content_hash, []).append(item)
        merged = 0
        for items in by_hash.values():
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

    def _rem_phase(
        self,
        now: datetime,
        conflicts: list[Conflict] | None = None,
        episodes: list[MemoryItem] | None = None,
    ) -> tuple[int, int]:
        """REM sleep: associative strengthening + conflict resolution.

        Walker & Stickgold (2004): REM sleep integrates new experiences into
        existing knowledge networks (associative links) and helps the brain
        reconcile incompatible information. We emulate:

        - links: episodes sharing >= 2 cues get a strengthened association
          (so later spreading activation reaches them more easily);
        - resolution: conflicting confident semantic memories both lose a
          little confidence, mirroring the "reconcile, don't keep both
          absolute" outcome of REM-mediated memory integration.
        """
        episodes = (
            episodes
            if episodes is not None
            else self.store.all_active(MemoryKind.EPISODIC)
        )
        episodes = [item for item in episodes if item.status is MemoryStatus.ACTIVE]
        links = 0
        pending_links: list[tuple[str, str, float]] = []
        if len(episodes) >= 2:
            # Cue -> items index: only pairs that share at least one cue are
            # examined, instead of every O(N^2) pair (each of which used to
            # rebuild a set for b). Cues shared by huge generic groups are
            # skipped entirely (a 10k-frequency cue would make every pair
            # "related" and cost ~60M iterations at 50k memories).
            cue_freq: dict[str, int] = {}
            for item in episodes:
                for cue in item.cues:
                    cue_freq[cue] = cue_freq.get(cue, 0) + 1
            cue_map: dict[str, list[MemoryItem]] = {}
            cue_freq_get = cue_freq.get
            for item in episodes:
                for cue in item.cues:
                    if cue_freq_get(cue, 0) > _REM_CUE_BUCKET_LIMIT:
                        continue
                    bucket = cue_map.get(cue)
                    if bucket is None:
                        bucket = []
                        cue_map[cue] = bucket
                    bucket.append(item)
            order = {item.id: index for index, item in enumerate(episodes)}
            # Index lists per cue let Counter.update() count shared cues
            # in C (small-int hashing) instead of Python dict.get per
            # (a, b, cue) triple (~58% faster at 100k episodes,
            # byte-for-byte same output order).
            cue_idx_map = {
                cue: [order[item.id] for item in bucket]
                for cue, bucket in cue_map.items()
            }
            cue_set_map = {
                cue: set(indices)
                for cue, indices in cue_idx_map.items()
            }
            counts: Counter[int] = Counter()
            cue_idx_get = cue_idx_map.get
            cue_set_get = cue_set_map.get
            for a_idx, a in enumerate(episodes):
                buckets: list[list[int]] = []
                buckets_append = buckets.append
                for cue in a.cues:
                    indices = cue_idx_get(cue)
                    if indices is not None:
                        buckets_append(indices)
                # An item in fewer than two cue buckets can never share
                # >= 2 cues with anyone, so its counting pass is skipped
                # (exact prune; ~18% faster at 100k episodes).
                if len(buckets) < 2:
                    continue
                if len(buckets) == 2:
                    # Most items land here: shared >= 2 means the
                    # candidate is in BOTH buckets, so scan the first
                    # bucket and test membership in the second (C-level
                    # set lookup). This preserves first-seen order
                    # exactly and skips the Counter pass (~47% faster at
                    # 100k episodes, byte-for-byte same output).
                    first = buckets[0]
                    second_set = None
                    for cue in a.cues:
                        other = cue_set_get(cue)
                        if other is not None:
                            if second_set is None:
                                second_set = other
                            else:
                                second_set = other
                                break
                    if second_set is not None:
                        for b_idx in first:
                            if b_idx <= a_idx:
                                continue
                            if b_idx in second_set:
                                pending_links.append(
                                    (a.id, episodes[b_idx].id, 1.0)
                                )
                                links += 1
                    continue
                counts.clear()
                a_id = a.id
                for indices in buckets:
                    counts.update(indices)
                for other_idx, shared in counts.items():
                    if (
                        shared < 2
                        or other_idx <= a_idx
                    ):
                        continue
                    b_id = episodes[other_idx].id
                    pending_links.append(
                        (a_id, b_id, 0.8 + 0.1 * shared)
                    )
                    links += 1
        if pending_links:
            # Keep the strongest associations when the budget binds: sort by
            # weight descending so early traversal order cannot starve
            # high-weight edges later in the store.
            pending_links.sort(key=lambda edge: edge[2], reverse=True)
            self.backend.add_links_many(
                pending_links[:_REM_LINK_BUDGET]
            )
            links = min(links, _REM_LINK_BUDGET)

        resolved = 0
        for conflict in (
            conflicts if conflicts is not None else self.detect_conflicts()
        ):
            a, b = conflict.a, conflict.b
            if a.confidence > 0.5 and b.confidence > 0.5:
                a.confidence = max(0.4, a.confidence - 0.1)
                b.confidence = max(0.4, b.confidence - 0.1)
                self.backend.update(a)
                self.backend.update(b)
                resolved += 1
        return links, resolved

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
        # backend.list already orders by seq DESC, so only the replay window
        # is loaded instead of the whole episodic store.
        episodes = self.backend.list_items(
            kind=MemoryKind.EPISODIC, limit=self.replay_window
        )
        replay_window_seconds = self.replay_recency_days * 86400.0
        replayed = 0
        updated: list[MemoryItem] = []
        for item in episodes:
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
            updated.append(item)
            replayed += 1
        if updated:
            # In-memory values were already applied above; the DB write is
            # the durable tail of an eventually-consistent replay (a failure
            # here only means the next sleep re-applies the same gains).
            try:
                self.backend.update_many(updated)
            except Exception as exc:  # noqa: BLE001
                _LOG.warning(
                    "sleep replay batch update failed: %s", exc
                )
        return replayed

    def reflect(
        self,
        summarizer: Callable[[list[str]], str] | None,
        now: datetime | None = None,
        semantic_items: list[MemoryItem] | None = None,
    ) -> list[MemoryItem]:
        """Reflection over supporting episodes (Park et al., 2023).

        Semantic facts backed by >= 2 linked episodes are re-written as an
        abstraction of those episodes. Without a summarizer this is a no-op.
        """
        if summarizer is None:
            return []
        now = now or utcnow()
        reflected: list[MemoryItem] = []
        facts = [
            fact
            for fact in (
                semantic_items
                if semantic_items is not None
                else self.store.all_active(MemoryKind.SEMANTIC)
            )
            if fact.status is MemoryStatus.ACTIVE
            and fact.evidence_count >= 2
        ]
        if not facts:
            return []
        # Batch graph lookup: one all_links + one get_many instead of a
        # SQL traversal per fact (2 queries x N facts).
        links = self.backend.all_links()
        neighbors: dict[str, set[str]] = {}
        for src, dst, _weight in links:
            neighbors.setdefault(src, set()).add(dst)
            neighbors.setdefault(dst, set()).add(src)
        needed: set[str] = set()
        for fact in facts:
            needed.update(neighbors.get(fact.id, ()))
        by_id = {
            item.id: item
            for item in self.backend.get_many(list(needed))
        }
        for fact in facts:
            episodes = [
                by_id[nid]
                for nid in neighbors.get(fact.id, ())
                if nid != fact.id
                and nid in by_id
                and by_id[nid].kind is MemoryKind.EPISODIC
                and by_id[nid].status is MemoryStatus.ACTIVE
            ]
            episodes.sort(key=lambda e: (e.seq, e.content))
            if len(episodes) > 20:
                episodes = episodes[:20]
            if len(episodes) < 2:
                continue
            episodes.sort(key=lambda e: (e.created_at, e.content))
            try:
                summary = (summarizer([e.content for e in episodes]) or "").strip()
            except Exception as exc:  # noqa: BLE001
                _LOG.debug("sleep summarizer failed: %s", exc)
                continue
            if not summary or summary == fact.content:
                continue
            fact.content = summary
            fact.content_hash = hash_content(summary)
            fact.updated_at = now
            self.backend.update(fact)
            reflected.append(fact)
        return reflected

    def _promote_episodic(
        self, now: datetime, episodes: list[MemoryItem] | None = None
    ) -> list[MemoryItem]:
        promoted: list[MemoryItem] = []
        episodes = (
            episodes
            if episodes is not None
            else self.store.all_active(MemoryKind.EPISODIC)
        )
        for item in episodes:
            if item.status is not MemoryStatus.ACTIVE:
                continue
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
                confidence=min(
                    1.0,
                    0.6 + 0.08 * evidence + (0.05 if item.affect else 0.0),
                ),
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

    def _prune_noise(
        self, now: datetime, episodes: list[MemoryItem] | None = None
    ) -> list[str]:
        recycled: list[str] = []
        episodes = (
            episodes
            if episodes is not None
            else self.store.all_active(MemoryKind.EPISODIC)
        )
        for item in episodes:
            if item.status is not MemoryStatus.ACTIVE:
                continue
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

    def detect_conflicts(
        self, semantic: list[MemoryItem] | None = None
    ) -> list[Conflict]:
        """Heuristic: confident semantic memories sharing a cue and topic.

        A shared cue alone is not a contradiction (two unrelated facts about
        the same person/tag coexist fine). The contents must also share at
        least one non-cue token before the pair is flagged.
        """
        semantic = [
            item
            for item in (
                semantic
                if semantic is not None
                else self.store.all_active(MemoryKind.SEMANTIC)
            )
            if item.status is MemoryStatus.ACTIVE
            and item.confidence >= self.conflict_min_confidence
        ]
        # Tokenize each content once; pair scans then only do set
        # intersections instead of re-tokenizing the same text per pair.
        item_tokens: dict[str, frozenset[str]] = {
            item.id: frozenset(tokenize(item.content)) for item in semantic
        }
        cue_tokens_cache: dict[str, frozenset[str]] = {}
        groups: dict[str, list[MemoryItem]] = {}
        for item in semantic:
            for cue in item.cues:
                groups.setdefault(cue, []).append(item)

        conflicts: list[Conflict] = []
        seen_pairs: set[frozenset[str]] = set()
        for cue, items in groups.items():
            for a, b in _bounded_pairs(items):
                if a.content_hash == b.content_hash:
                    continue
                pair = frozenset({a.id, b.id})
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                cue_tokens = cue_tokens_cache.get(cue)
                if cue_tokens is None:
                    cue_tokens = frozenset(tokenize(cue))
                    cue_tokens_cache[cue] = cue_tokens
                common = (
                    item_tokens[a.id] & item_tokens[b.id]
                ) - cue_tokens
                if not common:
                    continue
                conflicts.append(
                    Conflict(
                        a=a,
                        b=b,
                        reason=(
                            f"confident facts share cue '{cue}' and "
                            "topic but differ"
                        ),
                    )
                )
        return conflicts


__all__ = ["Conflict", "ConsolidationReport", "Consolidator"]
