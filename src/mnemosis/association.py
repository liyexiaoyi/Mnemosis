"""Associative recall: multi-cue indexing and a link graph.

Human principle #5: any cue (time, topic, people, keyword) can reach a
memory, and related memories are reachable from each other.
"""

from __future__ import annotations

import heapq
from operator import attrgetter

from .backend import Backend
from .types import MemoryItem


def _cue_bucket_limit(pool_size: int) -> int:
    """Adaptive generic-cue threshold for batch linking (~1% of the store).

    Auto-extracted cues like 用户/购买 appear in tens of thousands of
    memories; iterating them per item would turn batch ingestion into
    ~10^10 iterations at 100k scale. The threshold scales with the store
    (10k -> 200, 50k -> 500, 100k -> 1000) so small stores filter mid-freq
    noise and large stores keep locally discriminative cues.
    """
    return max(200, pool_size // 100)


class AssociationIndex:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend
        self._batch_pool: dict[str, MemoryItem] = {}
        self._batch_cue_freq: dict[str, int] = {}
        self._batch_cue_map: dict[str, list[MemoryItem]] = {}
        # Virtual append count for items already present in the initial
        # pool load: lets the "too generic" drop heuristic trigger at the
        # exact same iteration as the legacy implementation without
        # bloating buckets with duplicate references.
        self._batch_dup_count: dict[str, int] = {}
        self._batch_limit = 0
        self._batch_common: set[str] = set()

    def index(self, item: MemoryItem) -> None:
        self.backend.add_cues(item.id, item.cues)

    def link_related(
        self,
        item: MemoryItem,
        weight: float = 1.0,
        max_links: int = 64,
    ) -> list[MemoryItem]:
        """Link a new memory to existing memories sharing at least one cue.

        The per-item link budget is capped (sparse graph) so large stores do
        not explode into all-pairs edges; the most recent neighbors win.
        """
        related_ids: set[str] = set()
        for cue in item.cues:
            for other in self.backend.find_by_cue(cue):
                if other.id != item.id:
                    related_ids.add(other.id)
        related = [
            self.backend.get(rid) for rid in related_ids
        ]
        related = [other for other in related if other is not None]
        related.sort(
            # seq is globally unique per store, so the content tie-break
            # is dead code; an int key is much cheaper to build/compare.
            key=attrgetter("seq"),
            reverse=True,
        )
        for other in related[:max_links]:
            self.backend.add_link(item.id, other.id, weight)
            self.backend.add_link(other.id, item.id, weight)
        return related[:max_links]

    def link_related_batch(
        self,
        items: list[MemoryItem],
        weight: float = 1.0,
        max_links: int = 64,
    ) -> list[tuple[str, str, float]]:
        """Compute association pairs for many items in one pass.

        Loads the active store once, indexes cues in memory and returns
        (src, dst, weight) pairs for the caller to insert in a single
        transaction. Used by batch ingestion: the per-item path above costs
        one link transaction per edge (~128k transactions for 10k items),
        while this path costs one store load + one bulk insert.
        """
        if max_links <= 0:
            return []
        pool = self.backend.list()
        by_id = {item.id: item for item in pool}
        cue_freq: dict[str, int] = {}
        for item in pool:
            for cue in item.cues:
                cue_freq[cue] = cue_freq.get(cue, 0) + 1
        cue_map: dict[str, list[MemoryItem]] = {}
        limit = _cue_bucket_limit(len(pool))
        for item in pool:
            for cue in item.cues:
                if cue_freq.get(cue, 0) > limit:
                    continue
                cue_map.setdefault(cue, []).append(item)
        # Buckets are unique here (pool has no duplicate ids) and are
        # sorted ascending so the tail-scan below can skip candidates
        # that are dominated within their own bucket.
        for bucket in cue_map.values():
            bucket.sort(key=attrgetter("seq"))
        edge_set: set[tuple[str, str, float]] = set()
        for item in items:
            related_ids: set[str] = set()
            for cue in item.cues:
                bucket = cue_map.get(cue)
                if not bucket:
                    continue
                # A candidate ranked k-th in a seq-sorted bucket is
                # dominated by k higher-seq candidates from the same
                # bucket. The item itself occupies one of those slots
                # and is skipped below, so take max_links+1 entries.
                for other in bucket[-(max_links + 1) :]:
                    if other.id != item.id:
                        related_ids.add(other.id)
            related = [
                by_id[rid] for rid in related_ids if rid in by_id
            ]
            related.sort(
                key=attrgetter("seq"),
                reverse=True,
            )
            for other in related[:max_links]:
                edge_set.add((item.id, other.id, weight))
                edge_set.add((other.id, item.id, weight))
        return list(edge_set)

    def reset_batch(self) -> None:
        """Drop the incremental pool (call before/after a chunked run)."""
        self._batch_pool = {}
        self._batch_cue_freq = {}
        self._batch_cue_map = {}
        self._batch_dup_count = {}
        self._batch_limit = 0
        self._batch_common = set()

    def link_related_batch_incremental(
        self,
        items: list[MemoryItem],
        weight: float = 1.0,
        max_links: int = 64,
    ) -> list[tuple[str, str, float]]:
        """Incremental counterpart of ``link_related_batch``.

        The whole-store pool is loaded exactly once (on the first chunk);
        later chunks only add their new items to the in-memory index. This
        turns chunked ingestion from O(chunks * store) into O(store), which
        is the dominant cost at 100k scale. Call ``reset_batch`` before and
        after a chunked run.

        Note: the frequency limit is dynamic -- it tightens as the pool
        grows, and a bucket that outgrows the limit is dropped and banned.
        This is a heuristic approximation of the final-store frequency
        filter that prevents early bucket explosion on a cold start.
        """
        if max_links <= 0:
            return []
        if not self._batch_pool:
            pool = self.backend.list()
            self._batch_pool = {item.id: item for item in pool}
            self._batch_cue_freq = {}
            for item in pool:
                for cue in item.cues:
                    self._batch_cue_freq[cue] = (
                        self._batch_cue_freq.get(cue, 0) + 1
                    )
            self._batch_limit = _cue_bucket_limit(len(pool))
            self._batch_cue_map = {}
            self._batch_common = set()
            for item in pool:
                for cue in item.cues:
                    if self._batch_cue_freq.get(cue, 0) > self._batch_limit:
                        continue
                    self._batch_cue_map.setdefault(cue, []).append(item)
            # Unique pool buckets, sorted ascending; new items are
            # appended in seq order below, so the order stays sorted.
            for bucket in self._batch_cue_map.values():
                bucket.sort(key=attrgetter("seq"))
        # Tail-scan is only valid when the chunk's items arrive in
        # ascending seq order (the common episodic-import case). Semantic
        # dedup chunks can return pre-existing items with arbitrary seqs;
        # those fall back to the full scan, which is always correct.
        chunk_seq_sorted = all(
            items[i].seq <= items[i + 1].seq
            for i in range(len(items) - 1)
        )
        edge_set: set[tuple[str, str, float]] = set()
        for item in items:
            # Register the item before scanning so links inside this chunk
            # are found too; the self id is skipped below.
            is_pooled = item.id in self._batch_pool
            self._batch_pool[item.id] = item
            self._batch_limit = _cue_bucket_limit(len(self._batch_pool))
            for cue in item.cues:
                self._batch_cue_freq[cue] = (
                    self._batch_cue_freq.get(cue, 0) + 1
                )
                if (
                    cue in self._batch_common
                    or self._batch_cue_freq[cue] > self._batch_limit
                ):
                    continue
                bucket = self._batch_cue_map.setdefault(cue, [])
                virtual_len = len(bucket) + self._batch_dup_count.get(
                    cue, 0
                )
                if virtual_len >= self._batch_limit:
                    # This cue became too generic: drop its whole bucket and
                    # ban it for the rest of the run (same semantics as the
                    # full-store frequency filter in link_related_batch).
                    self._batch_common.add(cue)
                    self._batch_cue_map.pop(cue, None)
                    self._batch_dup_count.pop(cue, None)
                    continue
                if is_pooled:
                    # The item is already in the bucket from the initial
                    # store load. The original code appended a duplicate;
                    # count it virtually so the drop heuristic (which used
                    # the bloated length) stays byte-for-byte identical.
                    self._batch_dup_count[cue] = (
                        self._batch_dup_count.get(cue, 0) + 1
                    )
                else:
                    bucket.append(item)
            candidates: dict[str, MemoryItem] = {}
            for cue in item.cues:
                bucket = self._batch_cue_map.get(cue)
                if not bucket:
                    continue
                # Same tail argument as link_related_batch: candidates
                # outside the tail are dominated within their own bucket;
                # the +1 covers the slot taken by the item itself.
                scan = (
                    bucket[-(max_links + 1) :]
                    if chunk_seq_sorted
                    else bucket
                )
                for other in scan:
                    if other.id != item.id:
                        candidates[other.id] = other
            if candidates:
                if len(candidates) > max_links:
                    related = heapq.nlargest(
                        max_links,
                        candidates.values(),
                        key=attrgetter("seq"),
                    )
                else:
                    related = list(candidates.values())
                for other in related:
                    edge_set.add((item.id, other.id, weight))
                    edge_set.add((other.id, item.id, weight))
        return list(edge_set)

    def related(
        self, memory_id: str, depth: int = 1, max_nodes: int = 20
    ) -> list[MemoryItem]:
        return self.backend.related(memory_id, depth=depth, max_nodes=max_nodes)


__all__ = ["AssociationIndex"]
