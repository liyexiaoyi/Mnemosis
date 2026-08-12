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
        return len(self.purge_ids(before=before, limit=limit))

    def purge_ids(
        self, before: datetime | None = None, limit: int = 1000
    ) -> list[str]:
        """Hard-delete recycled memories and return the ids actually deleted.

        The status is re-checked atomically inside the backend delete, so a
        memory restored concurrently (between listing and deletion) is never
        lost.
        """
        purged: list[str] = []
        for item in self.backend.list(status=MemoryStatus.RECYCLED, limit=limit):
            if (
                before is None or item.created_at < before
            ) and self.backend.delete_if_recycled(item.id):
                purged.append(item.id)
        return purged


__all__ = ["RecycleBin"]
