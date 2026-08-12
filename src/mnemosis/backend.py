"""Storage backends: in-memory dict backend and SQLite backend.

Design rule: the core is `stdlib`-only. SQLite gives durable persistence
without external services. Requires SQLite >= 3.35 (upsert + WAL
checkpoint TRUNCATE); Python 3.9+ ships with a recent enough build.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from functools import wraps
from itertools import islice

from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    SourceRecord,
    _from_iso,
    normalize_cues,
    utcnow,
)

_BULK_DELETE_TEMP_INDEX_MIN = 2_000
"""Semantic batches at least this large get a temporary terms index during
bulk-mode DELETEs, since bulk mode defers idx_terms_memory."""

_UPDATE_BATCH = 500
"""Rows per transaction in update_many: bounds SQLite write-lock hold time
so concurrent writers (e.g. the reinforcement worker) do not stall long."""

_LOG = logging.getLogger(__name__)

_WRITE_BATCH = 2_000
"""Rows per transaction in add_many/add_cues_many: a single giant insert
can hold the write lock for seconds during large imports."""

_LINKS_CHUNK = 50_000
"""Rows per transaction in add_links_many outside bulk mode."""

_LINKS_BULK_CHUNK = 100_000
"""Rows per transaction in add_links_many during bulk import."""

_MEMORIES_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_memories_seq ON memories(seq)",
    "CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)",
    (
        "CREATE INDEX IF NOT EXISTS idx_memories_status "
        "ON memories(status)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_memories_status_kind "
        "ON memories(status, kind)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_memories_status_seq "
        "ON memories(status, seq)"
    ),
    (
        "CREATE INDEX IF NOT EXISTS idx_memories_status_importance "
        "ON memories(status, importance)"
    ),
)
"""Read-side memories indexes (self-heal + bulk-mode rebuild)."""

_CUES_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_cues_memory ON cues(memory_id)",
)
"""Cues reverse index (deletes/removals by memory_id)."""


def _locked(method):
    """Serialize a backend method on the instance lock (reentrant)."""

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class Backend(ABC):
    """Minimal storage contract used by the rest of Mnemosis."""

    @abstractmethod
    def add(self, item: MemoryItem) -> None: ...

    @abstractmethod
    def upsert(self, item: MemoryItem) -> MemoryItem:
        """Insert or merge by (kind, content_hash). Returns the stored item."""

    @abstractmethod
    def find_by_hash(
        self, kind: MemoryKind, content_hash: str
    ) -> MemoryItem | None: ...

    @abstractmethod
    def get(self, memory_id: str) -> MemoryItem | None: ...

    @abstractmethod
    def get_many(self, memory_ids: Iterable[str]) -> list[MemoryItem]: ...

    @abstractmethod
    def update(self, item: MemoryItem) -> None: ...

    @abstractmethod
    def delete(self, memory_id: str) -> None: ...

    @abstractmethod
    def delete_if_recycled(self, memory_id: str) -> bool: ...

    @abstractmethod
    def recycled_ids(
        self, *, limit: int = 1000, after_seq: int = -1
    ) -> list[tuple[int, str]]: ...

    @abstractmethod
    def index_terms(
        self, memory_id: str, terms: Iterable[str], kind: MemoryKind
    ) -> None: ...

    @abstractmethod
    def remove_terms(self, memory_id: str) -> None: ...

    @abstractmethod
    def find_by_terms(
        self, terms: Iterable[str], kind: MemoryKind | None
    ) -> set[str]: ...

    @abstractmethod
    def all_terms(self, kind: MemoryKind | None) -> dict[str, set[str]]: ...

    @abstractmethod
    def list(
        self,
        *,
        kind: MemoryKind | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        limit: int | None = None,
    ) -> list[MemoryItem]: ...

    @abstractmethod
    def add_cues(self, memory_id: str, cues: Iterable[str]) -> None: ...

    @abstractmethod
    def remove_cues(self, memory_id: str, cues: Iterable[str]) -> None: ...

    @abstractmethod
    def find_by_cue(self, cue: str) -> list[MemoryItem]: ...

    @abstractmethod
    def add_link(self, src: str, dst: str, weight: float = 1.0) -> None: ...

    @abstractmethod
    def link_weight(self, src: str, dst: str) -> float:
        """Return the weight of the src->dst link (0.0 if absent)."""

    @abstractmethod
    def all_links(self) -> list[tuple[str, str, float]]:
        """Return every directed link as (src, dst, weight)."""

    @abstractmethod
    def related(
        self, memory_id: str, depth: int = 1, max_nodes: int = 20
    ) -> list[MemoryItem]: ...

    @abstractmethod
    def stats(self) -> dict: ...

    def begin_bulk_mode(self) -> None:
        """Switch to fast bulk-import settings (no-op by default)."""

    def end_bulk_mode(self) -> None:
        """Restore normal settings after a bulk import (no-op by default)."""

    def warm_pages(
        self, stop: Callable[[], bool] | None = None
    ) -> None:
        """Warm OS/SQLite page caches for the main tables/indexes.

        No-op by default; SQLite backends scan cheap COUNT(*) queries so
        the first real query after startup does not pay the full cold
        page-load cost.
        """


class DictBackend(Backend):
    """In-memory backend for tests and quickstarts."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._items: dict[str, MemoryItem] = {}
        self._cues: dict[str, set[str]] = {}
        self._links: dict[tuple[str, str], float] = {}
        self._adj: dict[str, set[str]] = {}
        self._terms_index: dict[str, set[str]] = {}
        self._memory_terms: dict[str, set[str]] = {}
        self._settings: dict[str, str] = {}
        self._seq = 0

    @_locked
    def add(self, item: MemoryItem) -> None:
        self._seq += 1
        item.seq = self._seq
        self._items[item.id] = item

    @_locked
    def add_many(self, items: list[MemoryItem]) -> None:
        for item in items:
            self.add(item)

    @_locked
    def update_many(
        self,
        items: list[MemoryItem],
        *,
        busy_timeout_ms: int | None = None,
    ) -> None:
        # Memory backend: no disk lock, so busy_timeout_ms is intentionally
        # ignored (kept in the signature for caller compatibility).
        for item in items:
            self.update(item)

    @_locked
    def add_cues_many(
        self, pairs: Iterable[tuple[str, Iterable[str]]]
    ) -> None:
        for memory_id, cues in pairs:
            self.add_cues(memory_id, cues)

    @_locked
    def remove_cues_many(
        self, pairs: Iterable[tuple[str, Iterable[str]]]
    ) -> None:
        for memory_id, cues in pairs:
            self.remove_cues(memory_id, cues)

    @_locked
    def index_terms_many(
        self,
        pairs: Iterable[tuple[str, Iterable[str], MemoryKind]],
        *,
        replace: bool = True,
    ) -> None:
        for memory_id, terms, kind in pairs:
            if replace:
                self.remove_terms(memory_id)
            for term in set(terms):
                self._terms_index.setdefault(term, set()).add(memory_id)

    @_locked
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        return self._settings.get(key, default)

    @_locked
    def set_setting(self, key: str, value: str) -> None:
        self._settings[key] = value

    @_locked
    def upsert(self, item: MemoryItem) -> MemoryItem:
        existing = self.find_by_hash(item.kind, item.content_hash)
        if existing is None:
            self.add(item)
            return item
        _merge_stats(existing, item)
        self._seq += 1
        item.seq = self._seq
        self.add_cues(existing.id, item.cues)
        return existing

    @_locked
    def upsert_many(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """Bulk semantic dedupe; returns one stored item per input, in order."""
        index: dict[tuple[MemoryKind, str], MemoryItem] = {}
        for other in self._items.values():
            index.setdefault(
                (other.kind, other.content_hash), other
            )
        existing_by_hash = {
            (item.kind, item.content_hash): index.get(
                (item.kind, item.content_hash)
            )
            for item in items
        }
        new: list[MemoryItem] = []
        merged: list[MemoryItem] = []
        resolved: dict[tuple[MemoryKind, str], MemoryItem] = {}
        for item in items:
            existing = existing_by_hash.get(
                (item.kind, item.content_hash)
            )
            if existing is None:
                existing = resolved.get((item.kind, item.content_hash))
            if existing is None:
                new.append(item)
                resolved[(item.kind, item.content_hash)] = item
            else:
                _merge_stats(existing, item)
                merged.append(existing)
                resolved[(item.kind, item.content_hash)] = existing
        if new:
            self.add_many(new)
        if merged:
            self.update_many(merged)
            self.add_cues_many(
                (existing.id, existing.cues) for existing in merged
            )
        return [
            resolved[(item.kind, item.content_hash)] for item in items
        ]

    @_locked
    def find_by_hash(
        self, kind: MemoryKind, content_hash: str
    ) -> MemoryItem | None:
        for item in self._items.values():
            if item.kind == kind and item.content_hash == content_hash:
                return item
        return None

    @_locked
    def get(self, memory_id: str) -> MemoryItem | None:
        return self._items.get(memory_id)

    @_locked
    def get_many(self, memory_ids: Iterable[str]) -> list[MemoryItem]:
        items = [
            item
            for memory_id in memory_ids
            if (item := self._items.get(memory_id)) is not None
            and item.status == MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.seq, reverse=True)
        return items

    @_locked
    def update(self, item: MemoryItem) -> None:
        self._items[item.id] = item

    @_locked
    def delete(self, memory_id: str) -> None:
        self._items.pop(memory_id, None)
        self._drop_terms_for(memory_id)
        self._cues = {cue: ids for cue, ids in self._cues.items() if memory_id not in ids}
        self._links = {
            (a, b): w for (a, b), w in self._links.items() if a != memory_id and b != memory_id
        }
        self._adj.pop(memory_id, None)
        for neighbors in self._adj.values():
            neighbors.discard(memory_id)

    @_locked
    def delete_if_recycled(self, memory_id: str) -> bool:
        item = self._items.get(memory_id)
        if item is None or item.status is not MemoryStatus.RECYCLED:
            return False
        self.delete(memory_id)
        return True

    @_locked
    def recycled_ids(
        self, *, limit: int = 1000, after_seq: int = -1
    ) -> list[tuple[int, str]]:
        recycled = sorted(
            (item.seq, item.id)
            for item in self._items.values()
            if item.status is MemoryStatus.RECYCLED
            and item.seq > after_seq
        )
        return recycled[:limit]

    @_locked
    def index_terms(
        self, memory_id: str, terms: Iterable[str], kind: MemoryKind
    ) -> None:
        self.remove_terms(memory_id)
        term_set = set(terms)
        if term_set:
            self._memory_terms.setdefault(memory_id, set()).update(term_set)
        for term in term_set:
            self._terms_index.setdefault(term, set()).add(memory_id)

    @_locked
    def remove_terms(self, memory_id: str) -> None:
        self._drop_terms_for(memory_id)

    def _ensure_reverse_index(self) -> None:
        """Rebuild the reverse map once if missing (legacy/deserialized)."""
        if not self._memory_terms and self._terms_index:
            for term, ids in self._terms_index.items():
                for memory_id in ids:
                    self._memory_terms.setdefault(
                        memory_id, set()
                    ).add(term)

    def _drop_terms_for(self, memory_id: str) -> None:
        """Remove a memory from the term index using the reverse map (O(M))."""
        self._ensure_reverse_index()
        terms = self._memory_terms.pop(memory_id, None)
        if terms is None:
            return
        for term in terms:
            ids = self._terms_index.get(term)
            if ids is None:
                continue
            ids.discard(memory_id)
            if not ids:
                del self._terms_index[term]

    @_locked
    def find_by_terms(
        self, terms: Iterable[str], kind: MemoryKind | None
    ) -> set[str]:
        found: set[str] = set()
        for term in terms:
            found |= self._terms_index.get(term, set())
        if kind is None:
            return found
        return {
            memory_id
            for memory_id in found
            if self._items.get(memory_id) is not None
            and self._items[memory_id].kind == kind
        }

    @_locked
    def term_df(self, term: str, kind: MemoryKind | None) -> int:
        if kind is None:
            return len(self._terms_index.get(term, ()))
        return sum(
            1
            for memory_id in self._terms_index.get(term, ())
            if self._items.get(memory_id) is not None
            and self._items[memory_id].status is MemoryStatus.ACTIVE
            and (
                kind is None
                or self._items[memory_id].kind == kind
            )
        )

    @_locked
    def term_dfs(
        self, terms: Iterable[str], kind: MemoryKind | None
    ) -> dict[str, int]:
        return {
            term: self.term_df(term, kind)
            for term in set(terms)
        }

    @_locked
    def all_terms(self, kind: MemoryKind | None) -> dict[str, set[str]]:
        if kind is None:
            return {term: set(ids) for term, ids in self._terms_index.items()}
        return {
            term: {
                memory_id
                for memory_id in ids
                if self._items.get(memory_id) is not None
                and self._items[memory_id].kind == kind
            }
            for term, ids in self._terms_index.items()
        }

    @_locked
    def list(
        self,
        *,
        kind: MemoryKind | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        items = [
            item
            for item in self._items.values()
            if item.status == status and (kind is None or item.kind == kind)
        ]
        items.sort(key=lambda i: i.seq, reverse=True)
        return items[:limit] if limit is not None else items

    @_locked
    def count(
        self,
        *,
        kind: MemoryKind | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
    ) -> int:
        return sum(
            1
            for item in self._items.values()
            if item.status == status
            and (kind is None or item.kind == kind)
        )

    def warm_pages(
        self, stop: Callable[[], bool] | None = None
    ) -> None:
        """In-memory backend: nothing to warm."""

    @_locked
    def list_strongest(
        self,
        *,
        kind: MemoryKind | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        limit: int = 50,
    ) -> list[MemoryItem]:
        """Most important active memories.

        Ordered by importance only (no secondary recency sort) so the query
        stays a pure index scan on (status, importance); equal-importance
        ordering is arbitrary and fine for a fallback pool.
        """
        items = [
            item
            for item in self._items.values()
            if item.status == status
            and (kind is None or item.kind == kind)
        ]
        items.sort(
            key=lambda item: item.importance,
            reverse=True,
        )
        return items[:limit]

    @_locked
    def add_cues(self, memory_id: str, cues: Iterable[str]) -> None:
        for cue in normalize_cues(list(cues)):
            self._cues.setdefault(cue, set()).add(memory_id)

    @_locked
    def remove_cues(self, memory_id: str, cues: Iterable[str]) -> None:
        for cue in normalize_cues(list(cues)):
            ids = self._cues.get(cue)
            if ids:
                ids.discard(memory_id)

    @_locked
    def find_by_cue(self, cue: str) -> list[MemoryItem]:
        cue = cue.strip().lower()
        ids = sorted(self._cues.get(cue, set()))
        items = [self._items[i] for i in ids if i in self._items]
        items.sort(key=lambda item: (item.seq, item.content))
        return items

    @_locked
    def add_link(self, src: str, dst: str, weight: float = 1.0) -> None:
        if src == dst:
            return
        if src > dst:
            src, dst = dst, src
        self._links[(src, dst)] = max(self._links.get((src, dst), 0.0), weight)
        self._adj.setdefault(src, set()).add(dst)
        self._adj.setdefault(dst, set()).add(src)

    @_locked
    def add_links_many(
        self, pairs: Iterable[tuple[str, str, float]]
    ) -> None:
        for src, dst, weight in pairs:
            self.add_link(src, dst, weight)

    @_locked
    def link_weight(self, src: str, dst: str) -> float:
        if src > dst:
            src, dst = dst, src
        return self._links.get((src, dst), 0.0)

    @_locked
    def all_links(self) -> list[tuple[str, str, float]]:
        out: list[tuple[str, str, float]] = []
        for (a, b), w in self._links.items():
            out.append((a, b, w))
            out.append((b, a, w))
        return out

    @_locked
    def related(
        self, memory_id: str, depth: int = 1, max_nodes: int = 20
    ) -> list[MemoryItem]:
        frontier = {memory_id}
        seen: set[str] = set()
        for _ in range(max(1, depth)):
            if not frontier:
                break
            seen |= frontier
            neighbors: set[str] = set()
            for node in frontier:
                neighbors |= self._adj.get(node, set())
            frontier = neighbors - seen
        result = [self._items[i] for i in frontier if i in self._items]
        result.sort(key=lambda item: (item.seq, item.content))
        return result[:max_nodes]

    @_locked
    def stats(self) -> dict:
        active = [i for i in self._items.values() if i.status == MemoryStatus.ACTIVE]
        return {
            "total": len(self._items),
            "active": len(active),
            "episodic": sum(1 for i in active if i.kind == MemoryKind.EPISODIC),
            "semantic": sum(1 for i in active if i.kind == MemoryKind.SEMANTIC),
            "links": len(self._links),
            "cues": sum(len(v) for v in self._cues.values()),
            "avg_importance": round(
                sum(i.importance for i in active) / max(1, len(active)), 3
            ),
            "avg_strength": round(sum(i.strength for i in active) / max(1, len(active)), 3),
        }

    @_locked
    def count_links(self) -> int:
        """Number of canonical (undirected) link rows."""
        return len(self._links)

    @_locked
    def count_terms(self) -> int:
        """Number of term-index rows."""
        return sum(len(ids) for ids in self._terms_index.values())


class SQLiteBackend(Backend):
    """Durable SQLite backend (WAL mode). Pass ``":memory:"`` for tests."""

    _JSON_EACH_THRESHOLD = 64

    def __init__(self, path: str = "mnemosis.db") -> None:
        self._path = path
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._term_pending = 0
        self._bulk_terms_index_deferred = False
        self._bulk_write_batch = _WRITE_BATCH
        self._lock = threading.RLock()
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA temp_store=MEMORY")
        self._conn.execute("PRAGMA cache_size=-20000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()
        self._ensure_runtime_state()
        self._canonicalize_links_if_needed()
        self._json_each_ok = self._json_each_probe()

    def _create_schema(self) -> None:
        with self._conn:
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id            TEXT PRIMARY KEY,
                    kind          TEXT NOT NULL,
                    content       TEXT NOT NULL,
                    content_hash  TEXT NOT NULL,
                    source_json   TEXT NOT NULL,
                    cues_json     TEXT NOT NULL DEFAULT '[]',
                    created_at    TEXT NOT NULL,
                    last_access_at TEXT,
                    access_count  INTEGER NOT NULL DEFAULT 0,
                    importance    REAL NOT NULL DEFAULT 0.5,
                    strength      REAL NOT NULL DEFAULT 1.0,
                    confidence    REAL NOT NULL DEFAULT 1.0,
                    status        TEXT NOT NULL DEFAULT 'active',
                    last_review_at TEXT,
                    review_streak  INTEGER NOT NULL DEFAULT 0,
                    retrieval_successes INTEGER NOT NULL DEFAULT 0,
                    retrieval_failures  INTEGER NOT NULL DEFAULT 0
                )
                """
            )
            self._conn.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_semantic_hash
                ON memories(kind, content_hash) WHERE kind = 'semantic'
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_kind ON memories(kind)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_status ON memories(status)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_status_kind "
                "ON memories(status, kind)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS links (
                    src    TEXT NOT NULL,
                    dst    TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 1.0,
                    PRIMARY KEY (src, dst)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cues (
                    cue       TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    PRIMARY KEY (cue, memory_id)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cues_memory "
                "ON cues(memory_id)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS terms (
                    term      TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    kind      TEXT NOT NULL,
                    PRIMARY KEY (term, memory_id)
                )
                """
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_terms_memory ON terms(memory_id)"
            )
            self._conn.execute(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key   TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
                """
            )
        self._ensure_columns()
        self._conn.execute(
            # MAX(seq) is executed once per import chunk to allocate the
            # next seq; without this index each call scans the whole
            # memories table (super-linear bulk-import cost). The seq
            # column itself is added by _ensure_columns above.
            "CREATE INDEX IF NOT EXISTS idx_memories_seq ON memories(seq)"
        )

    @_locked
    def get_setting(self, key: str, default: str | None = None) -> str | None:
        row = self._conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else default

    @_locked
    def set_setting(self, key: str, value: str) -> None:
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value),
            )

    def _ensure_columns(self) -> None:
        """Migrate older databases by adding missing columns."""
        columns = [
            row[1]
            for row in self._conn.execute("PRAGMA table_info(memories)").fetchall()
        ]
        additions = {
            "context": "context TEXT",
            "affect": "affect TEXT",
            "evidence_count": "evidence_count INTEGER NOT NULL DEFAULT 1",
            "storage_strength": "storage_strength REAL NOT NULL DEFAULT 1.0",
            "updated_at": "updated_at TEXT",
            "revision_count": "revision_count INTEGER NOT NULL DEFAULT 0",
            "seq": "seq INTEGER NOT NULL DEFAULT 0",
            "last_review_at": "last_review_at TEXT",
            "review_streak": "review_streak INTEGER NOT NULL DEFAULT 0",
            "retrieval_successes": "retrieval_successes INTEGER NOT NULL DEFAULT 0",
            "retrieval_failures": "retrieval_failures INTEGER NOT NULL DEFAULT 0",
        }
        with self._conn:
            for name, ddl in additions.items():
                if name not in columns:
                    self._conn.execute(
                        f"ALTER TABLE memories ADD COLUMN {ddl}"
                    )
            # seq is added by the migration above, so this index must be
            # created after the column exists.
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_status_seq "
                "ON memories(status, seq)"
            )
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_status_importance "
                "ON memories(status, importance)"
            )

    @_locked
    def add(self, item: MemoryItem) -> None:
        # One atomic statement: MAX(seq)+1 is read and written in the same
        # INSERT, so concurrent writers (even other processes) cannot hand
        # out the same seq.
        with self._conn:
            self._conn.execute(_INSERT_SELECT_SQL, _item_row_params(item))
            row = self._conn.execute(
                "SELECT seq FROM memories WHERE id = ?", (item.id,)
            ).fetchone()
            item.seq = row["seq"]

    @_locked
    def _begin_immediate(self) -> None:
        """Acquire a write lock before the seq read, blocking other writers."""
        self._conn.execute("BEGIN IMMEDIATE")

    @_locked
    def add_many(self, items: list[MemoryItem]) -> None:
        """Insert many memories and their cues in bounded transactions.

        NOTE: no longer globally atomic -- an error mid-way leaves earlier
        batches committed. Retry callers must tolerate already-inserted ids
        (use a fresh run or upsert semantics).
        """
        if not items:
            return
        batch = self._bulk_write_batch
        for start in range(0, len(items), batch):
            chunk = items[start : start + batch]
            self._begin_immediate()
            try:
                row = self._conn.execute(
                    "SELECT COALESCE(MAX(seq), 0) AS next FROM memories"
                ).fetchone()
                seq = int(row["next"])
                rows: list[tuple] = []
                cue_rows: list[tuple[str, str]] = []
                for item in chunk:
                    seq += 1
                    item.seq = seq
                    rows.append(_item_row(item))
                    # MemoryItem.__post_init__ already normalized cues.
                    cue_rows.extend(
                        (cue, item.id)
                        for cue in item.cues
                    )
                self._conn.executemany(_INSERT_SQL, rows)
                if cue_rows:
                    self._conn.executemany(
                        "INSERT OR IGNORE INTO cues (cue, memory_id) "
                        "VALUES (?, ?)",
                        cue_rows,
                    )
                self._conn.commit()
            except Exception:
                self._conn.rollback()
                raise

    @_locked
    def upsert(self, item: MemoryItem) -> MemoryItem:
        existing = self.find_by_hash(item.kind, item.content_hash)
        if existing is None:
            self.add(item)
            return item
        self._begin_immediate()
        try:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM memories"
            ).fetchone()
            item.seq = row["next"]
            _merge_stats(existing, item)
            self._conn.execute(_UPDATE_SQL, _update_row(existing))
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        self.add_cues(existing.id, item.cues)
        return existing

    @_locked
    def upsert_many(self, items: list[MemoryItem]) -> list[MemoryItem]:
        """Bulk semantic dedupe; returns one stored item per input, in order."""
        if not items:
            return []
        existing_by_hash: dict[tuple[MemoryKind, str], MemoryItem] = {}
        by_kind: dict[str, list[MemoryItem]] = {}
        for item in items:
            by_kind.setdefault(item.kind.value, []).append(item)
        for kind_value, kind_items in by_kind.items():
            hashes = list({item.content_hash for item in kind_items})
            for start in range(0, len(hashes), 500):
                chunk = hashes[start : start + 500]
                placeholders = ",".join("?" for _ in chunk)
                rows = self._conn.execute(
                    "SELECT * FROM memories WHERE kind = ? "
                    f"AND content_hash IN ({placeholders})",
                    [kind_value] + chunk,
                ).fetchall()
                for row in rows:
                    item = _row_to_item(row)
                    existing_by_hash[(item.kind, item.content_hash)] = item
        new: list[MemoryItem] = []
        merged: list[MemoryItem] = []
        resolved: dict[tuple[MemoryKind, str], MemoryItem] = {}
        for item in items:
            existing = existing_by_hash.get(
                (item.kind, item.content_hash)
            )
            if existing is None:
                existing = resolved.get((item.kind, item.content_hash))
            if existing is None:
                new.append(item)
                resolved[(item.kind, item.content_hash)] = item
            else:
                _merge_stats(existing, item)
                merged.append(existing)
                resolved[(item.kind, item.content_hash)] = existing
        if new:
            self.add_many(new)
        if merged:
            self.update_many(merged)
            self.add_cues_many(
                (existing.id, existing.cues) for existing in merged
            )
        return [
            resolved[(item.kind, item.content_hash)] for item in items
        ]

    @_locked
    def find_by_hash(
        self, kind: MemoryKind, content_hash: str
    ) -> MemoryItem | None:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE kind = ? AND content_hash = ? LIMIT 1",
            (kind.value, content_hash),
        ).fetchone()
        return _row_to_item(row) if row else None

    @_locked
    def get(self, memory_id: str) -> MemoryItem | None:
        row = self._conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        return _row_to_item(row) if row else None

    @_locked
    def get_many(self, memory_ids: Iterable[str]) -> list[MemoryItem]:
        # Dedupe while preserving order; VALUES rows would otherwise repeat
        # when a caller passes the same id twice.
        ids = list(dict.fromkeys(memory_ids))
        if not ids:
            return []
        items: list[MemoryItem] = []
        for start in range(0, len(ids), 1000):
            chunk = ids[start : start + 1000]
            if len(chunk) >= self._JSON_EACH_THRESHOLD and self._json_each_ok:
                # json_each (SQLite 3.38+) passes the whole list as one JSON
                # parameter: no giant SQL string to parse, same PK-index
                # lookup, and no per-chunk VALUES bloat for very large lists
                # (1000 UUIDs serialize to ~40KB, far below SQLite limits).
                # A plain JOIN + WHERE status makes the planner scan the
                # (status, importance) index (70 ids -> ~324ms at 50k rows).
                # CROSS JOIN pins json_each as the driving table, so memories
                # is resolved by primary key and status is a post-predicate.
                # audit_query_plans still asserts the PK index name in the
                # EXPLAIN output, catching schema-level PK renames and any
                # well-meaning "simplification" back to a plain JOIN.
                rows = self._conn.execute(
                    "SELECT m.* FROM json_each(?) AS j "
                    "CROSS JOIN memories m ON m.id = j.value "
                    "WHERE m.status = ?",
                    (
                        json.dumps(chunk, default=str),
                        MemoryStatus.ACTIVE.value,
                    ),
                ).fetchall()
            else:
                # A long `id IN (...)` list can make SQLite scan the table on
                # small stores and after ANALYZE; a VALUES CTE join always
                # resolves through the primary key index.
                placeholders = "),(".join("?" for _ in chunk)
                rows = self._conn.execute(
                    "WITH cte(id) AS (VALUES (" + placeholders + ")) "
                    "SELECT m.* FROM memories m JOIN cte ON m.id = cte.id "
                    "WHERE m.status = ?",
                    (*chunk, MemoryStatus.ACTIVE.value),
                ).fetchall()
            items.extend(_row_to_item(row) for row in rows)
        items.sort(key=lambda item: item.seq, reverse=True)
        return items

    def _json_each_probe(self) -> bool:
        """Whether json_each is usable (older SQLite builds lack it)."""
        try:
            self._conn.execute(
                "SELECT value FROM json_each(?) LIMIT 1", ("[]",)
            ).fetchone()
            return True
        except sqlite3.OperationalError:
            return False

    def _ensure_runtime_state(self) -> None:
        """Self-heal after a crash inside a bulk import.

        begin_bulk_mode() drops idx_links_dst and weakens durability; if the
        process died before end_bulk_mode(), the missing index would silently
        slow every reverse-link traversal. Recreate it and restore the normal
        pragmas on the next open.
        """
        indexes = {
            row[1]
            for row in self._conn.execute(
                "PRAGMA index_list('links')"
            ).fetchall()
        }
        if "idx_links_dst" not in indexes:
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst)"
            )
        term_indexes = {
            row[1]
            for row in self._conn.execute(
                "PRAGMA index_list('terms')"
            ).fetchall()
        }
        if "idx_terms_memory" not in term_indexes:
            self._conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_terms_memory "
                "ON terms(memory_id)"
            )
        # Self-heal every memories index: bulk mode drops the read-side
        # ones for insert speed, and a crash before end_bulk_mode would
        # otherwise leave them missing forever.
        for index_sql in _MEMORIES_INDEX_SQL:
            self._conn.execute(index_sql)
        for index_sql in _CUES_INDEX_SQL:
            self._conn.execute(index_sql)
        sync_row = self._conn.execute("PRAGMA synchronous").fetchone()
        if sync_row is not None and sync_row[0] != 1:
            self._conn.execute("PRAGMA synchronous=NORMAL")
        cache_row = self._conn.execute("PRAGMA cache_size").fetchone()
        if cache_row is not None and cache_row[0] != -20000:
            self._conn.execute("PRAGMA cache_size=-20000")

    def _canonicalize_links_if_needed(self) -> None:
        """One-time migration of the links table to canonical edges.

        Older databases stored every undirected edge twice ((a,b) and
        (b,a)). New databases store one (min, max) row. On the first open
        of an old database, both directions are merged with the stronger
        weight and rewritten canonically; the ``links_canonical`` setting
        makes the migration run exactly once.
        """
        # Commit any implicit transaction left by schema setup so the
        # explicit BEGIN IMMEDIATE below cannot fail with "cannot start a
        # transaction within a transaction".
        self._conn.commit()
        # BEGIN IMMEDIATE serializes concurrent opens of an old database
        # (multi-process starts would otherwise race on the rewrite).
        self._conn.execute("BEGIN IMMEDIATE")
        try:
            row = self._conn.execute(
                "SELECT value FROM settings WHERE key = ?",
                ("links_canonical",),
            ).fetchone()
            if row is not None:
                self._conn.commit()
                return
            count = self._conn.execute(
                "SELECT COUNT(*) FROM links"
            ).fetchone()[0]
            if count:
                self._conn.execute(
                    """
                    CREATE TEMP TABLE links_old AS
                    SELECT src, dst, weight FROM links
                    """
                )
                self._conn.execute("DELETE FROM links")
                self._conn.execute(
                    """
                    INSERT INTO links (src, dst, weight)
                    SELECT
                        CASE WHEN src < dst THEN src ELSE dst END,
                        CASE WHEN src > dst THEN src ELSE dst END,
                        MAX(weight)
                    FROM links_old
                    WHERE src != dst
                    GROUP BY
                        CASE WHEN src < dst THEN src ELSE dst END,
                        CASE WHEN src > dst THEN src ELSE dst END
                    """
                )
                self._conn.execute("DROP TABLE links_old")
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                ("links_canonical", "1"),
            )
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise

    @_locked
    def begin_bulk_mode(self) -> None:
        """Fast bulk-import settings: no fsync per commit, bigger cache,
        and the reverse-link index deferred to a single rebuild at the end.

        Only for single-process imports; other connections would miss the
        dropped index until ``end_bulk_mode`` recreates it. Do NOT let
        another process/connection write to ``links`` while bulk mode is
        active. Links/terms are staged in TEMP tables and only copied to
        the main tables at end_bulk_mode, so concurrent readers see
        neither new links nor new terms until the import finishes.
        Semantic-heavy batches keep replace=True and pay a scan on
        DELETE (see index_terms_many).

        Callers MUST pair this with end_bulk_mode in a try/finally: an
        exception between the two leaves TEMP staging tables (and the
        weakened durability settings) in place until the connection
        closes.

        Warning: while bulk mode is active, read operations (recall,
        search, term_dfs) do NOT see the ingested links/terms until
        end_bulk_mode copies the staging tables. temp_store is switched
        to FILE so staging stays memory-lean; hosts with abundant RAM and
        slow temp disks may set PRAGMA temp_store=MEMORY beforehand.
        """
        if self._bulk_terms_index_deferred:
            raise RuntimeError(
                "bulk mode is already active; call end_bulk_mode first"
            )
        self._conn.execute("PRAGMA synchronous=OFF")
        self._conn.execute("PRAGMA cache_size=-200000")
        # TEMP staging tables would otherwise live in RAM
        # (temp_store=MEMORY is the global default); spill them to disk so
        # a 100k import stays memory-lean on NAS/VPS hosts.
        self._conn.execute("PRAGMA temp_store=FILE")
        self._conn.execute("DROP INDEX IF EXISTS idx_links_dst")
        self._conn.execute("DROP INDEX IF EXISTS idx_terms_memory")
        # Memories inserts maintain one index per secondary column; during
        # a large import (random-UUID PK inserts) that maintenance is the
        # dominant cost. Keep only the PK, semantic dedupe and seq indexes
        # (needed mid-import); the read-side indexes are rebuilt once at
        # end_bulk_mode.
        for index_name in (
            "idx_memories_kind",
            "idx_memories_status",
            "idx_memories_status_kind",
            "idx_memories_status_seq",
            "idx_memories_status_importance",
            "idx_cues_memory",
        ):
            self._conn.execute(f"DROP INDEX IF EXISTS {index_name}")
        # Stage links/terms in temp tables during the import: no PK
        # B-tree churn, no WAL growth, and one ordered copy at the end
        # replaces dozens of per-chunk transactions.
        self._conn.execute("DROP TABLE IF EXISTS links_bulk")
        self._conn.execute("DROP TABLE IF EXISTS terms_bulk")
        self._conn.execute(
            "CREATE TEMP TABLE links_bulk ("
            "src TEXT NOT NULL, dst TEXT NOT NULL, weight REAL NOT NULL)"
        )
        self._conn.execute(
            "CREATE TEMP TABLE terms_bulk ("
            "term TEXT NOT NULL, memory_id TEXT NOT NULL, "
            "kind TEXT NOT NULL)"
        )
        self._bulk_terms_index_deferred = True
        self._bulk_write_batch = 5_000

    @_locked
    def end_bulk_mode(self) -> None:
        """Restore durability settings, rebuild the deferred index, and
        checkpoint the WAL back into the main database file."""
        try:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO links (src, dst, weight) "
                    "SELECT src, dst, MAX(weight) FROM links_bulk "
                    "GROUP BY src, dst "
                    "ORDER BY src, dst "
                    "ON CONFLICT(src, dst) DO UPDATE "
                    "SET weight = MAX(weight, excluded.weight)"
                )
                self._conn.execute(
                    "INSERT OR IGNORE INTO terms (term, memory_id, kind) "
                    "SELECT term, memory_id, kind FROM terms_bulk "
                    "ORDER BY term, memory_id"
                )
        finally:
            # Always release the staged data and restore the connection,
            # even if the copy failed and rolled back.
            self._conn.execute("DROP TABLE IF EXISTS links_bulk")
            self._conn.execute("DROP TABLE IF EXISTS terms_bulk")
            try:
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_links_dst ON links(dst)"
                )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_terms_memory "
                    "ON terms(memory_id)"
                )
                for index_sql in _MEMORIES_INDEX_SQL:
                    self._conn.execute(index_sql)
                for index_sql in _CUES_INDEX_SQL:
                    self._conn.execute(index_sql)
            finally:
                # Durability settings must be restored even if the index
                # rebuild failed; a failed TRUNCATE checkpoint degrades
                # silently (a concurrent reader may hold the WAL).
                self._conn.execute("PRAGMA synchronous=NORMAL")
                self._conn.execute("PRAGMA cache_size=-20000")
                self._conn.execute("PRAGMA temp_store=MEMORY")
                try:
                    self._conn.execute(
                        "PRAGMA wal_checkpoint(TRUNCATE)"
                    )
                except sqlite3.OperationalError:
                    pass
            self._bulk_terms_index_deferred = False
            self._bulk_write_batch = _WRITE_BATCH

    @_locked
    def update(self, item: MemoryItem) -> None:
        with self._conn:
            self._conn.execute(_UPDATE_SQL, _update_row(item))

    @_locked
    def update_many(
        self,
        items: list[MemoryItem],
        *,
        busy_timeout_ms: int | None = None,
    ) -> None:
        """Update many memory rows in bounded transactions.

        Commits every ``_UPDATE_BATCH`` rows so the SQLite write lock is
        held briefly; a single huge transaction can stall concurrent
        writers for the whole batch. NOTE: this intentionally does NOT
        guarantee all-or-nothing atomicity across the whole batch -- an
        error mid-batch leaves earlier chunks committed.
        """
        if not items:
            return
        rows = []
        for item in items:
            rows.append(
                (
                    item.content,
                    item.content_hash,
                    json.dumps(item.source.to_dict()),
                    json.dumps(item.cues),
                    item.created_at.isoformat(),
                    item.last_access_at.isoformat() if item.last_access_at else None,
                    item.access_count,
                    item.importance,
                    item.strength,
                    item.confidence,
                    item.status.value,
                    item.context,
                    item.affect,
                    item.evidence_count,
                    item.storage_strength,
                    item.updated_at.isoformat() if item.updated_at else None,
                    item.revision_count,
                    item.seq,
                    item.last_review_at.isoformat() if item.last_review_at else None,
                    item.review_streak,
                    item.retrieval_successes,
                    item.retrieval_failures,
                    item.id,
                )
            )
        previous_timeout: int | None = None
        if busy_timeout_ms is not None:
            row = self._conn.execute("PRAGMA busy_timeout").fetchone()
            previous_timeout = row[0] if row is not None else None
            self._conn.execute(
                f"PRAGMA busy_timeout={int(busy_timeout_ms)}"
            )
        try:
            for start in range(0, len(rows), _UPDATE_BATCH):
                with self._conn:
                    self._conn.executemany(
                        """
                        UPDATE memories SET
                            content = ?, content_hash = ?, source_json = ?,
                            cues_json = ?,
                            created_at = ?, last_access_at = ?,
                            access_count = ?,
                            importance = ?, strength = ?, confidence = ?,
                            status = ?,
                            context = ?, affect = ?, evidence_count = ?,
                            storage_strength = ?, updated_at = ?,
                            revision_count = ?,
                            seq = ?, last_review_at = ?, review_streak = ?,
                            retrieval_successes = ?, retrieval_failures = ?
                        WHERE id = ?
                        """,
                        rows[start : start + _UPDATE_BATCH],
                    )
        finally:
            if busy_timeout_ms is not None and previous_timeout is not None:
                try:
                    self._conn.execute(
                        f"PRAGMA busy_timeout={previous_timeout}"
                    )
                except sqlite3.Error:
                    # Restoring the pragma must not mask the original error.
                    pass

    @_locked
    def delete(self, memory_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self._conn.execute("DELETE FROM cues WHERE memory_id = ?", (memory_id,))
            self._conn.execute("DELETE FROM links WHERE src = ? OR dst = ?", (memory_id, memory_id))
            self._conn.execute("DELETE FROM terms WHERE memory_id = ?", (memory_id,))

    @_locked
    def delete_if_recycled(self, memory_id: str) -> bool:
        """Atomically delete a memory only if it is still recycled.

        The status check and delete happen in one statement, so a concurrent
        restore() between check and delete cannot lose the memory.
        """
        with self._conn:
            cursor = self._conn.execute(
                "DELETE FROM memories WHERE id = ? AND status = 'recycled'",
                (memory_id,),
            )
            if cursor.rowcount == 0:
                return False
            self._conn.execute(
                "DELETE FROM cues WHERE memory_id = ?", (memory_id,)
            )
            self._conn.execute(
                "DELETE FROM links WHERE src = ? OR dst = ?",
                (memory_id, memory_id),
            )
            self._conn.execute(
                "DELETE FROM terms WHERE memory_id = ?", (memory_id,)
            )
            return True

    @_locked
    def recycled_ids(
        self, *, limit: int = 1000, after_seq: int = -1
    ) -> list[tuple[int, str]]:
        rows = self._conn.execute(
            "SELECT seq, id FROM memories "
            "WHERE status = 'recycled' AND seq > ? "
            "ORDER BY seq LIMIT ?",
            (after_seq, limit),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    @_locked
    def index_terms(
        self, memory_id: str, terms: Iterable[str], kind: MemoryKind
    ) -> None:
        normalized = sorted(set(terms))
        if not normalized:
            return
        self._conn.execute(
            "DELETE FROM terms WHERE memory_id = ?", (memory_id,)
        )
        self._conn.executemany(
            "INSERT OR REPLACE INTO terms (term, memory_id, kind) "
            "VALUES (?, ?, ?)",
            [(term, memory_id, kind.value) for term in normalized],
        )
        self._term_pending += 1
        if self._term_pending >= 200:
            self._conn.commit()
            self._term_pending = 0

    def index_terms_many(
        self,
        pairs: Iterable[tuple[str, Iterable[str], MemoryKind]],
        *,
        replace: bool = True,
    ) -> None:
        """Rebuild term rows for many memories in one atomic transaction."""
        entries: list[tuple[str, str, str]] = []
        ids: list[str] = []
        for memory_id, terms, kind in pairs:
            # Dedupe only; the global entries.sort() below provides the
            # PK-ordered stream, so a per-item sort would be wasted work.
            normalized = (
                terms
                if isinstance(terms, (set, frozenset))
                else set(terms)
            )
            if not normalized:
                continue
            ids.append(memory_id)
            entries.extend(
                (term, memory_id, kind.value) for term in normalized
            )
        if not entries:
            return
        # Deletes are small and share one transaction; inserts commit every
        # 200k rows so the WAL stays bounded (a single multi-million-row
        # transaction can balloon to multiple GB before checkpointing).
        if replace:
            # NOTE: in bulk mode idx_terms_memory is dropped for insert
            # speed, so these DELETEs scan when a semantic batch is large.
            # That is the intended trade-off: episodic imports
            # (replace=False) skip them entirely, and semantic upserts are
            # usually small.
            temp_index = False
            if (
                len(ids) >= _BULK_DELETE_TEMP_INDEX_MIN
                and self._bulk_terms_index_deferred
            ):
                self._conn.execute(
                    "CREATE INDEX idx_terms_memory ON terms(memory_id)"
                )
                temp_index = True
            try:
                with self._conn:
                    for start in range(0, len(ids), 500):
                        chunk = ids[start : start + 500]
                        placeholders = ",".join("?" for _ in chunk)
                        self._conn.execute(
                            "DELETE FROM terms "
                            f"WHERE memory_id IN ({placeholders})",
                            tuple(chunk),
                        )
            finally:
                if temp_index:
                    self._conn.execute("DROP INDEX idx_terms_memory")
        if self._bulk_terms_index_deferred:
            # Bulk import: stage into the temp table; end_bulk_mode copies
            # once, ordered by the PK, with the same OR IGNORE semantics.
            with self._conn:
                self._conn.executemany(
                    "INSERT INTO terms_bulk (term, memory_id, kind) "
                    "VALUES (?, ?, ?)",
                    entries,
                )
            return
        # Sorting by (term, memory_id) makes the PK B-tree append-ordered:
        # 2M random-order rows churn pages, ordered rows stream in.
        # Tuples already compare by (term, memory_id, kind); sorting
        # without key= avoids materialising 2M extra key tuples.
        entries.sort()
        for offset in range(0, len(entries), 200_000):
            with self._conn:
                self._conn.executemany(
                    # OR IGNORE is cheaper than REPLACE and equivalent here:
                    # the batch deletes its own ids first, and a memory's
                    # kind never changes.
                    "INSERT OR IGNORE INTO terms (term, memory_id, kind) "
                    "VALUES (?, ?, ?)",
                    entries[offset : offset + 200_000],
                )

    @_locked
    def remove_terms(self, memory_id: str) -> None:
        self._conn.execute(
            "DELETE FROM terms WHERE memory_id = ?", (memory_id,)
        )
        self._term_pending += 1
        if self._term_pending >= 200:
            self._conn.commit()
            self._term_pending = 0

    @_locked
    def find_by_terms(
        self, terms: Iterable[str], kind: MemoryKind | None
    ) -> set[str]:
        normalized = sorted(set(terms))
        if not normalized:
            return set()
        found: set[str] = set()
        for start in range(0, len(normalized), 500):
            chunk = normalized[start : start + 500]
            placeholders = ",".join("?" for _ in chunk)
            sql = (
                "SELECT DISTINCT memory_id FROM terms "
                f"WHERE term IN ({placeholders})"
            )
            params: list = list(chunk)
            if kind is not None:
                sql += " AND kind = ?"
                params.append(kind.value)
            rows = self._conn.execute(sql, tuple(params)).fetchall()
            found.update(row[0] for row in rows)
        return found

    @_locked
    def term_df(self, term: str, kind: MemoryKind | None) -> int:
        """Document frequency of one term without materialising its ids."""
        sql = (
            "SELECT COUNT(*) FROM terms t "
            "JOIN memories m ON m.id = t.memory_id "
            "WHERE t.term = ? AND m.status = ?"
        )
        params: list = [term, MemoryStatus.ACTIVE.value]
        if kind is not None:
            sql += " AND t.kind = ?"
            params.append(kind.value)
        return int(self._conn.execute(sql, params).fetchone()[0])

    @_locked
    def term_dfs(
        self, terms: Iterable[str], kind: MemoryKind | None
    ) -> dict[str, int]:
        """Document frequencies for many terms in one batched query.

        Counts terms-table rows (including recycled memories) instead of
        joining the memories table: the tiny overcount is a safe direction
        for idf/skip decisions and keeps the query on the terms PK index.
        """
        normalized = sorted(set(terms))
        if not normalized:
            return {}
        result: dict[str, int] = {}
        for start in range(0, len(normalized), 500):
            chunk = normalized[start : start + 500]
            placeholders = ",".join("?" for _ in chunk)
            sql = (
                "SELECT term, COUNT(*) AS n "
                f"FROM terms WHERE term IN ({placeholders})"
            )
            params: list = list(chunk)
            if kind is not None:
                sql += " AND kind = ?"
                params.append(kind.value)
            sql += " GROUP BY term"
            for row in self._conn.execute(sql, params).fetchall():
                result[row["term"]] = int(row["n"])
        return result

    @_locked
    def all_terms(self, kind: MemoryKind | None) -> dict[str, set[str]]:
        if kind is None:
            rows = self._conn.execute(
                "SELECT term, memory_id FROM terms"
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT term, memory_id FROM terms WHERE kind = ?",
                (kind.value,),
            ).fetchall()
        index: dict[str, set[str]] = {}
        for row in rows:
            index.setdefault(row["term"], set()).add(row["memory_id"])
        return index

    @_locked
    def list(
        self,
        *,
        kind: MemoryKind | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        limit: int | None = None,
    ) -> list[MemoryItem]:
        sql = "SELECT * FROM memories WHERE status = ?"
        params: list = [status.value]
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind.value)
        sql += " ORDER BY seq DESC"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_item(r) for r in rows]

    @_locked
    def count(
        self,
        *,
        kind: MemoryKind | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
    ) -> int:
        """Row count without loading any memory objects (cheap stats)."""
        sql = "SELECT COUNT(*) FROM memories WHERE status = ?"
        params: list = [status.value]
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind.value)
        return int(self._conn.execute(sql, params).fetchone()[0])

    def warm_pages(
        self, stop: Callable[[], bool] | None = None
    ) -> None:
        """Scan the main tables/indexes so their pages land in the OS cache.

        COUNT(*) scans the covering indexes (terms/links/cues/PK), which is
        exactly what a cold recall needs for candidate generation; full
        content data pages are fetched on demand for the handful of top
        results and are intentionally not pre-scanned (avoids polluting the
        OS cache with gigabytes of long text).

        Uses a dedicated connection for reading instead of the shared one,
        so the background warmup never contends with the main thread's lock.
        """
        if self._path == ":memory:":
            return
        try:
            conn = sqlite3.connect(
                self._path, check_same_thread=False, timeout=5.0
            )
        except sqlite3.Error:
            return
        try:
            for sql in (
                "SELECT COUNT(*) FROM memories",
                "SELECT COUNT(*) FROM memories WHERE status = 'active'",
                "SELECT COUNT(*) FROM terms",
                "SELECT COUNT(*) FROM links",
                "SELECT COUNT(*) FROM cues",
            ):
                if stop is not None and stop():
                    break
                conn.execute(sql).fetchone()
        except sqlite3.Error as exc:
            _LOG.debug("warmup scan skipped: %s", exc)
        finally:
            conn.close()

    @_locked
    def count_links(self) -> int:
        """Number of canonical (undirected) link rows."""
        return int(
            self._conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        )

    @_locked
    def count_terms(self) -> int:
        """Number of term-index rows."""
        return int(
            self._conn.execute("SELECT COUNT(*) FROM terms").fetchone()[0]
        )

    @_locked
    def list_strongest(
        self,
        *,
        kind: MemoryKind | None = None,
        status: MemoryStatus = MemoryStatus.ACTIVE,
        limit: int = 50,
    ) -> list[MemoryItem]:
        """Most important active memories (importance, then recency)."""
        sql = (
            "SELECT * FROM memories WHERE status = ? "
            "ORDER BY importance DESC"
        )
        params: list = [status.value]
        if kind is not None:
            sql += " AND kind = ?"
            params.append(kind.value)
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        rows = self._conn.execute(sql, params).fetchall()
        return [_row_to_item(r) for r in rows]

    @_locked
    def add_cues(self, memory_id: str, cues: Iterable[str]) -> None:
        normalized = normalize_cues(list(cues))
        if not normalized:
            return
        with self._conn:
            self._conn.executemany(
                "INSERT OR IGNORE INTO cues (cue, memory_id) VALUES (?, ?)",
                [(cue, memory_id) for cue in normalized],
            )

    @_locked
    def add_cues_many(self, pairs: Iterable[tuple[str, Iterable[str]]]) -> None:
        """Add cues for many memories in bounded transactions (batch-atomic)."""
        rows = [
            (cue, memory_id)
            for memory_id, cues in pairs
            for cue in normalize_cues(list(cues))
        ]
        if not rows:
            return
        batch = self._bulk_write_batch
        for start in range(0, len(rows), batch):
            with self._conn:
                self._conn.executemany(
                    "INSERT OR IGNORE INTO cues (cue, memory_id) "
                    "VALUES (?, ?)",
                    rows[start : start + batch],
                )

    @_locked
    def remove_cues(self, memory_id: str, cues: Iterable[str]) -> None:
        normalized = normalize_cues(list(cues))
        if not normalized:
            return
        with self._conn:
            self._conn.executemany(
                "DELETE FROM cues WHERE memory_id = ? AND cue = ?",
                [(memory_id, cue) for cue in normalized],
            )

    @_locked
    def remove_cues_many(self, pairs: Iterable[tuple[str, Iterable[str]]]) -> None:
        """Remove cues from many memories in one atomic transaction."""
        rows = [
            (memory_id, cue)
            for memory_id, cues in pairs
            for cue in normalize_cues(list(cues))
        ]
        if not rows:
            return
        with self._conn:
            self._conn.executemany(
                "DELETE FROM cues WHERE memory_id = ? AND cue = ?",
                rows,
            )

    @_locked
    def find_by_cue(self, cue: str) -> list[MemoryItem]:
        cue = cue.strip().lower()
        rows = self._conn.execute(
            """
            SELECT m.* FROM memories m
            JOIN cues c ON c.memory_id = m.id
            WHERE c.cue = ?
            """,
            (cue,),
        ).fetchall()
        rows.sort(key=lambda row: (row["seq"], row["content"]))
        return [_row_to_item(r) for r in rows]

    @_locked
    def add_link(self, src: str, dst: str, weight: float = 1.0) -> None:
        if src == dst:
            return
        # Undirected edge: store one canonical (min, max) row so the
        # links table is half the size of the old two-direction format.
        if src > dst:
            src, dst = dst, src
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO links (src, dst, weight) VALUES (?, ?, ?)
                ON CONFLICT(src, dst) DO UPDATE SET weight = MAX(weight, excluded.weight)
                """,
                (src, dst, weight),
            )

    @_locked
    def add_links_many(
        self, pairs: Iterable[tuple[str, str, float]]
    ) -> None:
        """Insert many directed links in chunked transactions."""
        def _canonical_rows():
            for src, dst, weight in pairs:
                if src == dst:
                    continue
                if src > dst:
                    src, dst = dst, src
                yield src, dst, weight

        rows = _canonical_rows()
        # Bulk mode (deferred term index, big page cache, synchronous=OFF)
        # is single-process import only: a 100k-row transaction adds only
        # ~10-20MB of WAL and rolls back cheaply, but halves the number of
        # commits versus 50k. Normal mode (sleep consolidation etc.) keeps
        # the smaller chunk so write-lock holds stay short.
        chunk_size = (
            _LINKS_BULK_CHUNK
            if self._bulk_terms_index_deferred
            else _LINKS_CHUNK
        )
        if self._bulk_terms_index_deferred:
            # Bulk import: stage into a temp table (no PK churn, no WAL
            # growth); end_bulk_mode copies it once, PK-ordered, and the
            # upsert keeps the exact weight-MAX semantics.
            with self._conn:
                self._conn.executemany(
                    "INSERT INTO links_bulk (src, dst, weight) "
                    "VALUES (?, ?, ?)",
                    rows,
                )
            return
        while True:
            chunk = list(islice(rows, chunk_size))
            if not chunk:
                return
            # Sort by the PK (src, dst) so B-tree inserts stream in page
            # order instead of churning random pages per row. Keying on
            # (src, dst) keeps weights (possibly NaN) out of the sort.
            chunk.sort(key=lambda row: (row[0], row[1]))
            with self._conn:
                self._conn.executemany(
                    """
                    INSERT INTO links (src, dst, weight) VALUES (?, ?, ?)
                    ON CONFLICT(src, dst) DO UPDATE SET weight = MAX(weight, excluded.weight)
                    """,
                    chunk,
                )

    @_locked
    def link_weight(self, src: str, dst: str) -> float:
        if src > dst:
            src, dst = dst, src
        row = self._conn.execute(
            "SELECT weight FROM links WHERE src = ? AND dst = ?",
            (src, dst),
        ).fetchone()
        return float(row["weight"]) if row else 0.0

    @_locked
    def all_links(self) -> list[tuple[str, str, float]]:
        rows = self._conn.execute(
            "SELECT src, dst, weight FROM links "
            "UNION ALL SELECT dst, src, weight FROM links"
        ).fetchall()
        # The canonical row is mirrored in SQL so graph consumers see the
        # same undirected edge from both sides as the old format.
        return [
            (row["src"], row["dst"], float(row["weight"]))
            for row in rows
        ]

    @_locked
    def related(
        self, memory_id: str, depth: int = 1, max_nodes: int = 20
    ) -> list[MemoryItem]:
        frontier = {memory_id}
        seen: set[str] = set()
        for _ in range(max(1, depth)):
            if not frontier:
                break
            placeholders = ",".join("?" for _ in frontier)
            rows = self._conn.execute(
                f"""
                SELECT dst FROM links WHERE src IN ({placeholders})
                UNION
                SELECT src FROM links WHERE dst IN ({placeholders})
                """,
                list(frontier) * 2,
            ).fetchall()
            seen |= frontier
            frontier = {r[0] for r in rows} - seen
        if not frontier:
            return []
        placeholders = ",".join("?" for _ in frontier)
        rows = self._conn.execute(
            f"""
            SELECT * FROM memories WHERE id IN ({placeholders})
            ORDER BY seq, content
            LIMIT ?
            """,
            [*frontier, max_nodes],
        ).fetchall()
        return [_row_to_item(r) for r in rows]

    def query_plan(self, sql: str, params: tuple = ()) -> str:
        """EXPLAIN QUERY PLAN summary, used by the CI planner audit."""
        rows = self._conn.execute(
            "EXPLAIN QUERY PLAN " + sql, params
        ).fetchall()
        return " | ".join(row[3] or "" for row in rows)

    def audit_query_plans(self) -> dict[str, str]:
        """Run EXPLAIN QUERY PLAN over the core hot-path queries.

        CI asserts that each one still uses its intended index; this guards
        against silent planner regressions (e.g. the get_many status-filter
        scan that appeared once the memories table passed ~10k rows).
        """
        return {
            "get_many": self.query_plan(
                "WITH cte(id) AS (VALUES (?), (?)) "
                "SELECT m.* FROM memories m JOIN cte ON m.id = cte.id "
                "WHERE m.status = ?",
                ("a", "b", "active"),
            ),
            "get_many_long": self.query_plan(
                "WITH cte(id) AS (VALUES ("
                + "),(".join("?" for _ in range(50))
                + ")) SELECT m.* FROM memories m JOIN cte ON m.id = cte.id "
                "WHERE m.status = ?",
                tuple(f"id{i}" for i in range(50)) + ("active",),
            ),
            "get_many_json": self.query_plan(
                "SELECT m.* FROM json_each(?) AS j "
                "CROSS JOIN memories m ON m.id = j.value "
                "WHERE m.status = ?",
                ("[]", "active"),
            ),
            "list_recent": self.query_plan(
                "SELECT * FROM memories WHERE status = ? "
                "ORDER BY seq DESC LIMIT ?",
                ("active", 10),
            ),
            "list_strongest": self.query_plan(
                "SELECT * FROM memories WHERE status = ? "
                "ORDER BY importance DESC LIMIT ?",
                ("active", 10),
            ),
            "find_by_cue": self.query_plan(
                "SELECT m.* FROM cues c JOIN memories m "
                "ON m.id = c.memory_id WHERE c.cue = ? AND m.status = ?",
                ("cue", "active"),
            ),
            "find_by_terms": self.query_plan(
                "SELECT DISTINCT m.id FROM terms t JOIN memories m "
                "ON m.id = t.memory_id WHERE t.term = ? AND m.status = ? "
                "LIMIT 10",
                ("term", "active"),
            ),
            "term_df": self.query_plan(
                "SELECT COUNT(*) FROM terms t JOIN memories m "
                "ON m.id = t.memory_id WHERE t.term = ? AND m.status = ?",
                ("term", "active"),
            ),
            "related_links": self.query_plan(
                "SELECT dst FROM links WHERE src IN (?)",
                ("a",),
            ),
            "related_memories": self.query_plan(
                "SELECT * FROM memories WHERE id IN (?) "
                "ORDER BY seq, content LIMIT ?",
                ("a", 20),
            ),
        }

    @_locked
    def stats(self) -> dict:
        active_rows = self._conn.execute(
            "SELECT kind, COUNT(*) AS n FROM memories "
            "WHERE status = ? GROUP BY kind",
            (MemoryStatus.ACTIVE.value,),
        ).fetchall()
        active = sum(row["n"] for row in active_rows)
        episodic = sum(
            row["n"]
            for row in active_rows
            if row["kind"] == MemoryKind.EPISODIC.value
        )
        semantic = sum(
            row["n"]
            for row in active_rows
            if row["kind"] == MemoryKind.SEMANTIC.value
        )
        avg = self._conn.execute(
            "SELECT COALESCE(AVG(importance), 0), COALESCE(AVG(strength), 0) "
            "FROM memories WHERE status = ?",
            (MemoryStatus.ACTIVE.value,),
        ).fetchone()
        total = self._conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        links = self._conn.execute("SELECT COUNT(*) FROM links").fetchone()[0]
        cues = self._conn.execute("SELECT COUNT(*) FROM cues").fetchone()[0]
        return {
            "total": total,
            "active": active,
            "episodic": episodic,
            "semantic": semantic,
            "links": links,
            "cues": cues,
            "avg_importance": round(float(avg[0]), 3),
            "avg_strength": round(float(avg[1]), 3),
        }

    @_locked
    def close(self) -> None:
        if self._term_pending:
            self._conn.commit()
            self._term_pending = 0
        self._conn.close()

    def __enter__(self) -> SQLiteBackend:  # noqa: PYI034 (3.10 CI)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _merge_stats(target: MemoryItem, incoming: MemoryItem) -> None:
    """Merge an incoming duplicate into the stored item (semantic dedupe)."""
    target.importance = max(target.importance, incoming.importance)
    target.confidence = max(target.confidence, incoming.confidence)
    target.strength = max(target.strength, incoming.strength)
    target.access_count += incoming.access_count
    target.cues = normalize_cues(target.cues + incoming.cues)
    target.evidence_count = max(target.evidence_count, incoming.evidence_count)
    target.storage_strength = max(
        target.storage_strength, incoming.storage_strength
    )
    target.revision_count = max(target.revision_count, incoming.revision_count)
    target.seq = min(target.seq, incoming.seq) if incoming.seq else target.seq
    if incoming.updated_at and (
        target.updated_at is None or incoming.updated_at > target.updated_at
    ):
        target.updated_at = incoming.updated_at
    if incoming.source.trust > target.source.trust:
        target.source = incoming.source
    if incoming.last_access_at and (
        target.last_access_at is None or incoming.last_access_at > target.last_access_at
    ):
        target.last_access_at = incoming.last_access_at


def _item_row(item: MemoryItem) -> tuple:
    return (
        item.id,
        item.kind.value,
        item.content,
        item.content_hash,
        json.dumps(item.source.to_dict()),
        json.dumps(item.cues),
        item.created_at.isoformat(),
        item.last_access_at.isoformat() if item.last_access_at else None,
        item.access_count,
        item.importance,
        item.strength,
        item.confidence,
        item.status.value,
        item.context,
        item.affect,
        item.evidence_count,
        item.storage_strength,
        item.updated_at.isoformat() if item.updated_at else None,
        item.revision_count,
        item.seq,
        item.last_review_at.isoformat() if item.last_review_at else None,
        item.review_streak,
        item.retrieval_successes,
        item.retrieval_failures,
    )


def _item_row_params(item: MemoryItem) -> tuple:
    """All ``_item_row`` fields except ``seq`` (assigned atomically by SQL)."""
    row = _item_row(item)
    return row[:19] + row[20:]


def _update_row(item: MemoryItem) -> tuple:
    """Parameters for ``_UPDATE_SQL`` (all fields followed by the id)."""
    return (
        item.content,
        item.content_hash,
        json.dumps(item.source.to_dict()),
        json.dumps(item.cues),
        item.created_at.isoformat(),
        item.last_access_at.isoformat() if item.last_access_at else None,
        item.access_count,
        item.importance,
        item.strength,
        item.confidence,
        item.status.value,
        item.context,
        item.affect,
        item.evidence_count,
        item.storage_strength,
        item.updated_at.isoformat() if item.updated_at else None,
        item.revision_count,
        item.seq,
        item.last_review_at.isoformat() if item.last_review_at else None,
        item.review_streak,
        item.retrieval_successes,
        item.retrieval_failures,
        item.id,
    )


_INSERT_SQL = """
INSERT INTO memories (
    id, kind, content, content_hash, source_json, cues_json,
    created_at, last_access_at, access_count, importance,
    strength, confidence, status, context, affect, evidence_count,
    storage_strength, updated_at, revision_count, seq,
    last_review_at, review_streak, retrieval_successes,
    retrieval_failures
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
          ?, ?, ?, ?)
"""

_INSERT_SELECT_SQL = """
INSERT INTO memories (
    id, kind, content, content_hash, source_json, cues_json,
    created_at, last_access_at, access_count, importance,
    strength, confidence, status, context, affect, evidence_count,
    storage_strength, updated_at, revision_count, seq,
    last_review_at, review_streak, retrieval_successes,
    retrieval_failures
) SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
         COALESCE(MAX(seq), 0) + 1, ?, ?, ?, ?
  FROM memories
"""

_UPDATE_SQL = """
UPDATE memories SET
    content = ?, content_hash = ?, source_json = ?, cues_json = ?,
    created_at = ?, last_access_at = ?, access_count = ?,
    importance = ?, strength = ?, confidence = ?, status = ?,
    context = ?, affect = ?, evidence_count = ?,
    storage_strength = ?, updated_at = ?, revision_count = ?,
    seq = ?, last_review_at = ?, review_streak = ?,
    retrieval_successes = ?, retrieval_failures = ?
WHERE id = ?
"""


def _row_to_item(row: sqlite3.Row | None) -> MemoryItem | None:
    if row is None:
        return None
    # Trusted fast path: rows were written through MemoryItem, so every
    # value is already normalized/clamped. Skipping __post_init__
    # validation (normalize_cues, clamps, enum re-parsing) makes 100k-scale
    # loads several times faster. IMPORTANT: keep this field list in sync
    # with MemoryItem; test_row_fast_path_fields covers the invariant.
    item = MemoryItem.__new__(MemoryItem)
    item.id = row["id"]
    item.kind = MemoryKind(row["kind"])
    item.content = row["content"]
    item.content_hash = row["content_hash"]
    item.source = SourceRecord.from_dict(json.loads(row["source_json"]))
    item.cues = json.loads(row["cues_json"])
    item.created_at = _from_iso(row["created_at"]) or utcnow()
    item.last_access_at = _from_iso(row["last_access_at"])
    item.access_count = row["access_count"]
    item.importance = row["importance"]
    item.strength = row["strength"]
    item.confidence = row["confidence"]
    item.status = MemoryStatus(row["status"])
    item.context = row["context"]
    item.affect = row["affect"]
    item.evidence_count = row["evidence_count"]
    item.storage_strength = row["storage_strength"]
    item.updated_at = _from_iso(row["updated_at"])
    item.revision_count = row["revision_count"]
    item.seq = row["seq"]
    item.last_review_at = _from_iso(row["last_review_at"])
    item.review_streak = row["review_streak"]
    item.retrieval_successes = row["retrieval_successes"]
    item.retrieval_failures = row["retrieval_failures"]
    return item


def make_backend(memory_file: str | None = None) -> Backend:
    if memory_file is None:
        return DictBackend()
    return SQLiteBackend(memory_file)


__all__ = ["Backend", "DictBackend", "SQLiteBackend", "make_backend"]
