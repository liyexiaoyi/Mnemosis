"""Associative recall: multi-cue indexing and a link graph.

Human principle #5: any cue (time, topic, people, keyword) can reach a
memory, and related memories are reachable from each other.
"""

from __future__ import annotations

from .backend import Backend
from .types import MemoryItem


class AssociationIndex:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

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
            key=lambda other: (other.seq, other.content),
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
        pool = self.backend.list()
        by_id = {item.id: item for item in pool}
        cue_map: dict[str, list[MemoryItem]] = {}
        for item in pool:
            for cue in item.cues:
                cue_map.setdefault(cue, []).append(item)
        edge_set: set[tuple[str, str, float]] = set()
        for item in items:
            related_ids: set[str] = set()
            for cue in item.cues:
                for other in cue_map.get(cue, ()):
                    if other.id != item.id:
                        related_ids.add(other.id)
            related = [
                by_id[rid] for rid in related_ids if rid in by_id
            ]
            related.sort(
                key=lambda other: (other.seq, other.content),
                reverse=True,
            )
            for other in related[:max_links]:
                edge_set.add((item.id, other.id, weight))
                edge_set.add((other.id, item.id, weight))
        return list(edge_set)

    def related(
        self, memory_id: str, depth: int = 1, max_nodes: int = 20
    ) -> list[MemoryItem]:
        return self.backend.related(memory_id, depth=depth, max_nodes=max_nodes)


__all__ = ["AssociationIndex"]
