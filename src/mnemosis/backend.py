"""Storage backends: in-memory dict backend and SQLite backend.

Design rule: the core is `stdlib`-only. SQLite gives durable persistence
without external services.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from abc import ABC, abstractmethod
from collections.abc import Iterable
from functools import wraps

from .types import (
    MemoryItem,
    MemoryKind,
    MemoryStatus,
    normalize_cues,
)


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


class DictBackend(Backend):
    """In-memory backend for tests and quickstarts."""

    def __init__(self) -> None:
        self._items: dict[str, MemoryItem] = {}
        self._cues: dict[str, set[str]] = {}
        self._links: dict[tuple[str, str], float] = {}
        self._adj: dict[str, set[str]] = {}
        self._terms_index: dict[str, set[str]] = {}
        self._settings: dict[str, str] = {}
        self._seq = 0

    def add(self, item: MemoryItem) -> None:
        self._seq += 1
        item.seq = self._seq
        self._items[item.id] = item

    def add_many(self, items: list[MemoryItem]) -> None:
        for item in items:
            self.add(item)

    def update_many(self, items: list[MemoryItem]) -> None:
        for item in items:
            self.update(item)

    def add_cues_many(
        self, pairs: Iterable[tuple[str, Iterable[str]]]
    ) -> None:
        for memory_id, cues in pairs:
            self.add_cues(memory_id, cues)

    def remove_cues_many(
        self, pairs: Iterable[tuple[str, Iterable[str]]]
    ) -> None:
        for memory_id, cues in pairs:
            self.remove_cues(memory_id, cues)

    def get_setting(self, key: str, default: str | None = None) -> str | None:
        return self._settings.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self._settings[key] = value

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

    def find_by_hash(
        self, kind: MemoryKind, content_hash: str
    ) -> MemoryItem | None:
        for item in self._items.values():
            if item.kind == kind and item.content_hash == content_hash:
                return item
        return None

    def get(self, memory_id: str) -> MemoryItem | None:
        return self._items.get(memory_id)

    def get_many(self, memory_ids: Iterable[str]) -> list[MemoryItem]:
        items = [
            item
            for memory_id in memory_ids
            if (item := self._items.get(memory_id)) is not None
            and item.status == MemoryStatus.ACTIVE
        ]
        items.sort(key=lambda item: item.seq, reverse=True)
        return items

    def update(self, item: MemoryItem) -> None:
        self._items[item.id] = item

    def delete(self, memory_id: str) -> None:
        self._items.pop(memory_id, None)
        self._terms_index = {
            term: ids
            for term, ids in self._terms_index.items()
            if memory_id not in ids
        }
        self._cues = {cue: ids for cue, ids in self._cues.items() if memory_id not in ids}
        self._links = {
            (a, b): w for (a, b), w in self._links.items() if a != memory_id and b != memory_id
        }
        self._adj.pop(memory_id, None)
        for neighbors in self._adj.values():
            neighbors.discard(memory_id)

    def index_terms(
        self, memory_id: str, terms: Iterable[str], kind: MemoryKind
    ) -> None:
        self.remove_terms(memory_id)
        for term in set(terms):
            self._terms_index.setdefault(term, set()).add(memory_id)

    def remove_terms(self, memory_id: str) -> None:
        self._terms_index = {
            term: ids
            for term, ids in self._terms_index.items()
            if memory_id not in ids
        }

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

    def add_cues(self, memory_id: str, cues: Iterable[str]) -> None:
        for cue in normalize_cues(list(cues)):
            self._cues.setdefault(cue, set()).add(memory_id)

    def remove_cues(self, memory_id: str, cues: Iterable[str]) -> None:
        for cue in normalize_cues(list(cues)):
            ids = self._cues.get(cue)
            if ids:
                ids.discard(memory_id)

    def find_by_cue(self, cue: str) -> list[MemoryItem]:
        cue = cue.strip().lower()
        ids = sorted(self._cues.get(cue, set()))
        items = [self._items[i] for i in ids if i in self._items]
        items.sort(key=lambda item: (item.seq, item.content))
        return items

    def add_link(self, src: str, dst: str, weight: float = 1.0) -> None:
        if src == dst:
            return
        self._links[(src, dst)] = max(self._links.get((src, dst), 0.0), weight)
        self._adj.setdefault(src, set()).add(dst)
        self._adj.setdefault(dst, set()).add(src)

    def link_weight(self, src: str, dst: str) -> float:
        return self._links.get((src, dst), 0.0)

    def all_links(self) -> list[tuple[str, str, float]]:
        return [(a, b, w) for (a, b), w in self._links.items()]

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


def _locked(method):
    @wraps(method)
    def wrapper(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)

    return wrapper


class SQLiteBackend(Backend):
    """Durable SQLite backend (WAL mode). Pass ``":memory:"`` for tests."""

    def __init__(self, path: str = "mnemosis.db") -> None:
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._term_pending = 0
        self._lock = threading.RLock()
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA busy_timeout=5000")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA temp_store=MEMORY")
        self._conn.execute("PRAGMA cache_size=-20000")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._create_schema()

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

    @_locked
    def add(self, item: MemoryItem) -> None:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM memories"
        ).fetchone()
        item.seq = row["next"]
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO memories (
                    id, kind, content, content_hash, source_json, cues_json,
                    created_at, last_access_at, access_count, importance,
                    strength, confidence, status, context, affect, evidence_count,
                    storage_strength, updated_at, revision_count, seq,
                    last_review_at, review_streak, retrieval_successes,
                    retrieval_failures
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?)
                """,
                _item_row(item),
            )

    @_locked
    def add_many(self, items: list[MemoryItem]) -> None:
        """Insert many memories and their cues in one atomic transaction."""
        if not items:
            return
        with self._conn:
            row = self._conn.execute(
                "SELECT COALESCE(MAX(seq), 0) AS next FROM memories"
            ).fetchone()
            seq = int(row["next"])
            rows: list[tuple] = []
            cue_rows: list[tuple[str, str]] = []
            for item in items:
                seq += 1
                item.seq = seq
                rows.append(_item_row(item))
                cue_rows.extend(
                    (cue, item.id) for cue in normalize_cues(item.cues)
                )
            self._conn.executemany(
                """
                INSERT INTO memories (
                    id, kind, content, content_hash, source_json, cues_json,
                    created_at, last_access_at, access_count, importance,
                    strength, confidence, status, context, affect, evidence_count,
                    storage_strength, updated_at, revision_count, seq,
                    last_review_at, review_streak, retrieval_successes,
                    retrieval_failures
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?)
                """,
                rows,
            )
            if cue_rows:
                self._conn.executemany(
                    "INSERT OR IGNORE INTO cues (cue, memory_id) VALUES (?, ?)",
                    cue_rows,
                )

    @_locked
    def upsert(self, item: MemoryItem) -> MemoryItem:
        existing = self.find_by_hash(item.kind, item.content_hash)
        if existing is None:
            self.add(item)
            return item
        row = self._conn.execute(
            "SELECT COALESCE(MAX(seq), 0) + 1 AS next FROM memories"
        ).fetchone()
        item.seq = row["next"]
        _merge_stats(existing, item)
        self.update(existing)
        self.add_cues(existing.id, item.cues)
        return existing

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
        ids = list(memory_ids)
        if not ids:
            return []
        items: list[MemoryItem] = []
        for start in range(0, len(ids), 500):
            chunk = ids[start : start + 500]
            placeholders = ",".join("?" for _ in chunk)
            rows = self._conn.execute(
                f"SELECT * FROM memories WHERE status = 'active' "
                f"AND id IN ({placeholders})",
                tuple(chunk),
            ).fetchall()
            items.extend(_row_to_item(row) for row in rows)
        items.sort(key=lambda item: item.seq, reverse=True)
        return items

    @_locked
    def update(self, item: MemoryItem) -> None:
        with self._conn:
            self._conn.execute(
                """
                UPDATE memories SET
                    content = ?, content_hash = ?, source_json = ?, cues_json = ?,
                    created_at = ?, last_access_at = ?, access_count = ?,
                    importance = ?, strength = ?, confidence = ?, status = ?,
                    context = ?, affect = ?, evidence_count = ?,
                    storage_strength = ?, updated_at = ?, revision_count = ?,
                    seq = ?, last_review_at = ?, review_streak = ?,
                    retrieval_successes = ?, retrieval_failures = ?
                WHERE id = ?
                """,
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
                ),
            )

    @_locked
    def update_many(self, items: list[MemoryItem]) -> None:
        """Update many memory rows in one atomic transaction."""
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
        with self._conn:
            self._conn.executemany(
                """
                UPDATE memories SET
                    content = ?, content_hash = ?, source_json = ?, cues_json = ?,
                    created_at = ?, last_access_at = ?, access_count = ?,
                    importance = ?, strength = ?, confidence = ?, status = ?,
                    context = ?, affect = ?, evidence_count = ?,
                    storage_strength = ?, updated_at = ?, revision_count = ?,
                    seq = ?, last_review_at = ?, review_streak = ?,
                    retrieval_successes = ?, retrieval_failures = ?
                WHERE id = ?
                """,
                rows,
            )

    @_locked
    def delete(self, memory_id: str) -> None:
        with self._conn:
            self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            self._conn.execute("DELETE FROM cues WHERE memory_id = ?", (memory_id,))
            self._conn.execute("DELETE FROM links WHERE src = ? OR dst = ?", (memory_id, memory_id))
            self._conn.execute("DELETE FROM terms WHERE memory_id = ?", (memory_id,))

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
        """Add cues for many memories in one atomic transaction."""
        rows = [
            (cue, memory_id)
            for memory_id, cues in pairs
            for cue in normalize_cues(list(cues))
        ]
        if not rows:
            return
        with self._conn:
            self._conn.executemany(
                "INSERT OR IGNORE INTO cues (cue, memory_id) VALUES (?, ?)",
                rows,
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
        with self._conn:
            self._conn.execute(
                """
                INSERT INTO links (src, dst, weight) VALUES (?, ?, ?)
                ON CONFLICT(src, dst) DO UPDATE SET weight = MAX(weight, excluded.weight)
                """,
                (src, dst, weight),
            )

    @_locked
    def link_weight(self, src: str, dst: str) -> float:
        row = self._conn.execute(
            "SELECT weight FROM links WHERE src = ? AND dst = ?",
            (src, dst),
        ).fetchone()
        return float(row["weight"]) if row else 0.0

    @_locked
    def all_links(self) -> list[tuple[str, str, float]]:
        rows = self._conn.execute(
            "SELECT src, dst, weight FROM links"
        ).fetchall()
        return [(r["src"], r["dst"], float(r["weight"])) for r in rows]

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
            """,
            list(frontier),
        ).fetchall()
        return [_row_to_item(r) for r in rows][:max_nodes]

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

    def __enter__(self) -> SQLiteBackend:
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


def _row_to_item(row: sqlite3.Row | None) -> MemoryItem | None:
    if row is None:
        return None
    data = {
        "id": row["id"],
        "kind": row["kind"],
        "content": row["content"],
        "content_hash": row["content_hash"],
        "source": json.loads(row["source_json"]),
        "cues": json.loads(row["cues_json"]),
        "created_at": row["created_at"],
        "last_access_at": row["last_access_at"],
        "access_count": row["access_count"],
        "importance": row["importance"],
        "strength": row["strength"],
        "confidence": row["confidence"],
        "status": row["status"],
        "context": row["context"],
        "affect": row["affect"],
        "evidence_count": row["evidence_count"],
        "storage_strength": row["storage_strength"],
        "updated_at": row["updated_at"],
        "revision_count": row["revision_count"],
        "seq": row["seq"],
        "last_review_at": row["last_review_at"],
        "review_streak": row["review_streak"],
        "retrieval_successes": row["retrieval_successes"],
        "retrieval_failures": row["retrieval_failures"],
    }
    return MemoryItem.from_dict(data)


def make_backend(memory_file: str | None = None) -> Backend:
    if memory_file is None:
        return DictBackend()
    return SQLiteBackend(memory_file)


__all__ = ["Backend", "DictBackend", "SQLiteBackend", "make_backend"]
