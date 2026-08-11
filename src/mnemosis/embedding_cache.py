"""Optional persistent embedding cache (SQLite, zero extra dependencies).

Wraps any :class:`~mnemosis.embedding.Embedder` and stores computed vectors
on disk keyed by text hash, so repeated recalls on the same corpus skip the
embedding call entirely. Useful with cloud/local embedding APIs.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import threading
from array import array
from collections import OrderedDict

from .embedding import Embedder


class SqliteEmbeddingCache(Embedder):
    """Embedder wrapper with a persistent SQLite vector cache."""

    def __init__(
        self,
        embedder: Embedder,
        path: str,
        table: str = "vectors",
        max_memory: int = 10000,
        batch_size: int = 200,
    ) -> None:
        if not re.fullmatch(r"[A-Za-z0-9_]+", table):
            raise ValueError("table name must match [A-Za-z0-9_]+")
        self.embedder = embedder
        self.path = path
        self.table = table
        self.max_memory = max_memory
        self.batch_size = batch_size
        self.cache_key = path
        self._lock = threading.Lock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute(
            f"CREATE TABLE IF NOT EXISTS {table} "
            "(key TEXT PRIMARY KEY, vec BLOB NOT NULL, dim INT NOT NULL)"
        )
        self._conn.commit()
        self._memory: OrderedDict[str, list[float]] = OrderedDict()
        self._pending = 0

    @staticmethod
    def _key(text: str) -> str:
        return hashlib.sha256(text.encode("utf-8")).hexdigest()

    def embed(self, text: str) -> list[float]:
        key = self._key(text)
        cached = self._memory.get(key)
        if cached is not None:
            return cached
        row = None
        vector = None
        with self._lock:
            row = self._conn.execute(
                f"SELECT vec, dim FROM {self.table} WHERE key = ?", (key,)
            ).fetchone()
            if row is not None:
                dim = row[1]
                if len(row[0]) != dim * 8:
                    raise ValueError(
                        f"corrupt cached vector for key {key[:12]}"
                    )
                vec_array = array("d")
                vec_array.frombytes(row[0])
                vector = vec_array.tolist()
        if vector is None:
            vector = self.embedder.embed(text)  # outside the lock
        with self._lock:
            if row is None:
                self._conn.execute(
                    f"INSERT OR REPLACE INTO {self.table} (key, vec, dim) "
                    "VALUES (?, ?, ?)",
                    (key, array("d", vector).tobytes(), len(vector)),
                )
                self._pending += 1
                if self._pending >= self.batch_size:
                    self._conn.commit()
                    self._pending = 0
            self._memory[key] = vector
            self._memory.move_to_end(key)
            if len(self._memory) > self.max_memory:
                self._memory.popitem(last=False)
            return vector

    def __enter__(self) -> SqliteEmbeddingCache:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def flush(self) -> None:
        with self._lock:
            if self._pending:
                self._conn.commit()
                self._pending = 0

    def close(self) -> None:
        self.flush()
        self._conn.close()


__all__ = ["SqliteEmbeddingCache"]
