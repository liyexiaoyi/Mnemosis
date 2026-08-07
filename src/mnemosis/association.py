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
        self, item: MemoryItem, weight: float = 1.0
    ) -> list[MemoryItem]:
        """Link a new memory to existing active memories sharing at least one cue."""
        related_ids: set[str] = set()
        for cue in item.cues:
            for other in self.backend.find_by_cue(cue):
                if other.id != item.id:
                    related_ids.add(other.id)
        related: list[MemoryItem] = []
        for rid in related_ids:
            other = self.backend.get(rid)
            if other is None:
                continue
            self.backend.add_link(item.id, other.id, weight)
            self.backend.add_link(other.id, item.id, weight)
            related.append(other)
        return related

    def related(
        self, memory_id: str, depth: int = 1, max_nodes: int = 20
    ) -> list[MemoryItem]:
        return self.backend.related(memory_id, depth=depth, max_nodes=max_nodes)


__all__ = ["AssociationIndex"]

