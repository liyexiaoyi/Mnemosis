"""Active forgetting with a recycle bin.

Human principle #7: forgetting is a feature. Deletions are recoverable and
never silent.
"""

from __future__ import annotations

from datetime import datetime

from .backend import Backend
from .types import MemoryItem, MemoryStatus


class RecycleBin:
    def __init__(self, backend: Backend) -> None:
        self.backend = backend

    def trash(self, memory_id: str) -> bool:
        item = self.backend.get(memory_id)
        if item is None or item.status is MemoryStatus.RECYCLED:
            return False
        item.status = MemoryStatus.RECYCLED
        self.backend.update(item)
        return True

    def restore(self, memory_id: str) -> bool:
        item = self.backend.get(memory_id)
        if item is None or item.status is not MemoryStatus.RECYCLED:
            return False
        item.status = MemoryStatus.ACTIVE
        self.backend.update(item)
        return True

    def list_trash(self, limit: int = 50) -> list[MemoryItem]:
        return self.backend.list(status=MemoryStatus.RECYCLED, limit=limit)

    def purge(self, before: datetime | None = None, limit: int = 1000) -> int:
        """Hard-delete recycled memories; optionally only those older than `before`."""
        count = 0
        for item in self.backend.list(status=MemoryStatus.RECYCLED, limit=limit):
            if before is None or item.created_at < before:
                self.backend.delete(item.id)
                count += 1
        return count


__all__ = ["RecycleBin"]

