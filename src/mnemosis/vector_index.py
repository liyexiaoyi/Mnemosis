"""Zero-dependency vector index with exact scan up to a size budget.

Motivation: dense recall in :mod:`mnemosis.hybrid` used to scan every active
memory and embed/score them at query time. This module moves the work to
write time: vectors are persisted in SQLite. For small and medium stores
(default up to 100k vectors and 512MB of float32 matrix), queries run an
**exact** cosine scan over a lazily built in-memory matrix, so recall is
100% by construction. Only above that budget does the index fall back to
LSH buckets (random hyperplane projections, Charikar 2002-style) plus exact
cosine re-ranking; within the exact budget it still falls back to a full
scan when buckets miss too many candidates, and beyond the budget it serves
the best bucket candidates instead of materialising a multi-GB matrix.
Vectors are persisted as float32 (legacy float64 files are read
transparently), so cosine scores are computed in float32 precision.
numpy is optional; the fallback is pure Python.
"""

from __future__ import annotations

import logging
import random
import sqlite3
import struct
import threading
from array import array
from typing import Any

_LOG = logging.getLogger(__name__)


class VectorIndex:
    """Persistent LSH-bucket vector index backed by SQLite."""

    def __init__(
        self,
        path: str | None = None,
        *,
        dim: int | None = None,
        bits: int = 13,
        buckets_per_item: int = 8,
        seed: int = 42,
        probe: int = 0,
        full_scan_threshold: int = 10000,
        exact_scan_limit: int = 100_000,
        # 100k x 1024-dim is ~410MB in float32; 512MB is a memory-lean
        # default. Higher-dim embeddings can raise the budget explicitly.
        exact_scan_max_bytes: int = 512 * 1024 * 1024,
        fallback_to_full_scan: bool = False,
        max_candidates: int = 30000,
    ) -> None:
        self.path = path or ":memory:"
        self.bits = bits
        self.buckets_per_item = buckets_per_item
        self.seed = seed
        self.probe = probe
        self.full_scan_threshold = full_scan_threshold
        self.exact_scan_limit = max(0, int(exact_scan_limit))
        self.exact_scan_max_bytes = max(0, int(exact_scan_max_bytes))
        self.fallback_to_full_scan = bool(fallback_to_full_scan)
        self.max_candidates = max_candidates
        self._dim = dim
        self._lock = threading.RLock()
        self._pending = 0
        self._matrix_cache: tuple[
            list[str], Any, Any, list[tuple[str, bytes]]
        ] | None = None
        self._count: int | None = None
        self._numpy_available = self._probe_numpy()
        if not self._numpy_available:
            # Pure-Python exact scans are ~1000x slower than numpy; cap the
            # exact range so a 100k store cannot stall on a Python loop.
            self.exact_scan_limit = min(self.exact_scan_limit, 1000)
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value BLOB)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS vectors "
            "(memory_id TEXT PRIMARY KEY, vec BLOB NOT NULL)"
        )
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS buckets "
            "(bucket INTEGER NOT NULL, memory_id TEXT NOT NULL)"
        )
        self._conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_buckets ON buckets(bucket)"
        )
        self._conn.commit()

    # -- projection / signatures -----------------------------------------

    def _projection(self) -> list[list[float]]:
        row = self._conn.execute(
            "SELECT value FROM meta WHERE key='proj'"
        ).fetchone()
        if row is not None:
            dim = struct.unpack("i", row[0][:4])[0]
            self._dim = dim
            flat = array("d")
            flat.frombytes(row[0][4:])
            return [
                list(flat[i * dim : (i + 1) * dim])
                for i in range(self.bits)
            ]
        if self._dim is None:
            raise ValueError("dim must be known before the first add")
        rng = random.Random(self.seed)
        projection = [
            [rng.gauss(0.0, 1.0) for _ in range(self._dim)]
            for _ in range(self.bits)
        ]
        flat = array("d")
        for vector in projection:
            flat.extend(vector)
        self._conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('proj', ?)",
            (struct.pack("i", self._dim) + flat.tobytes(),),
        )
        self._conn.commit()
        return projection

    def _signature(self, vector: list[float], projection: list[list[float]]) -> int:
        signature = 0
        for bit_index, weights in enumerate(projection):
            dot = 0.0
            for value, weight in zip(vector, weights):
                dot += value * weight
            if dot > 0:
                signature |= 1 << bit_index
        return signature

    def _dimension(self) -> int | None:
        """Dimension of stored vectors, read from meta on reopen."""
        if self._dim is not None:
            return self._dim
        with self._lock:
            row = self._conn.execute(
                "SELECT value FROM meta WHERE key='dim'"
            ).fetchone()
            if row is not None and row[0] is not None and len(row[0]) >= 4:
                self._dim = struct.unpack("i", row[0][:4])[0]
                return self._dim
            row = self._conn.execute(
                "SELECT value FROM meta WHERE key='proj'"
            ).fetchone()
            if row is None or row[0] is None or len(row[0]) < 4:
                # Last-resort legacy recovery: infer the dimension from the
                # stored blob length (4 bytes/element = new float32 format,
                # 8 bytes/element = legacy float64 format).
                blob = self._conn.execute(
                    "SELECT length(vec) FROM vectors LIMIT 1"
                ).fetchone()
                if blob is None or blob[0] is None:
                    return None
                length = int(blob[0])
                # Prefer the legacy float64 interpretation first: old
                # stores wrote 8 bytes/element and only exist without meta
                # in hand-rolled databases.
                if length > 0 and length % 8 == 0:
                    self._dim = length // 8
                    return self._dim
                if length > 0 and length % 4 == 0:
                    self._dim = length // 4
                    return self._dim
                return None
            self._dim = struct.unpack("i", row[0][:4])[0]
            return self._dim

    @staticmethod
    def _probe_numpy() -> bool:
        try:
            import numpy  # noqa: F401

            return True
        except ImportError:
            return False

    def _has_numpy(self) -> bool:
        return self._numpy_available

    def _persist_dim(self, dim: int) -> None:
        """Store the vector dimension independently of the LSH projection.

        No commit here: the caller's transaction (or the next write path)
        commits together with the projection metadata.
        """
        self._conn.execute(
            "INSERT OR REPLACE INTO meta (key, value) VALUES ('dim', ?)",
            (struct.pack("i", dim),),
        )

    @staticmethod
    def _rotate(signature: int, shift: int, bits: int) -> int:
        mask = (1 << bits) - 1
        return ((signature << shift) | (signature >> (bits - shift))) & mask

    def _bucket_ids(self, signature: int) -> list[int]:
        shifts = [
            (self.bits * index) // self.buckets_per_item
            for index in range(self.buckets_per_item)
        ]
        return [self._rotate(signature, shift, self.bits) for shift in shifts]

    def _neighbour_signatures(self, signature: int) -> list[int]:
        signatures = [signature]
        if self.probe >= 1:
            for bit in range(self.bits):
                signatures.append(signature ^ (1 << bit))
        return signatures

    # -- write / read -----------------------------------------------------

    def add(self, memory_id: str, vector: list[float]) -> None:
        with self._lock:
            self._matrix_cache = None
            self._count = None
            new_dim = self._dim is None
            if self._dim is None:
                self._dim = len(vector)
            projection = self._projection()
            signature = self._signature(vector, projection)
            with self._conn:
                if new_dim:
                    self._persist_dim(self._dim)
                self._conn.execute(
                    "DELETE FROM buckets WHERE memory_id = ?", (memory_id,)
                )
                self._conn.execute(
                    "INSERT OR REPLACE INTO vectors (memory_id, vec) "
                    "VALUES (?, ?)",
                    (memory_id, array("f", vector).tobytes()),
                )
                self._conn.executemany(
                    "INSERT INTO buckets (bucket, memory_id) VALUES (?, ?)",
                    [
                        (bucket, memory_id)
                        for bucket in self._bucket_ids(signature)
                    ],
                )
            self._pending += 1
            if self._pending >= 100:
                self._conn.commit()
                self._pending = 0

    def add_many(self, entries: list[tuple[str, list[float]]]) -> None:
        """Add many vectors in one lock + one commit (batch ingestion)."""
        if not entries:
            return
        with self._lock:
            self._matrix_cache = None
            self._count = None
            new_dim = self._dim is None
            if self._dim is None:
                self._dim = len(entries[0][1])
            projection = self._projection()
            for offset in range(0, len(entries), 5000):
                chunk = entries[offset : offset + 5000]
                vector_rows: list[tuple[str, bytes]] = []
                bucket_rows: list[tuple[int, str]] = []
                ids: list[str] = []
                for memory_id, vector in chunk:
                    ids.append(memory_id)
                    signature = self._signature(vector, projection)
                    vector_rows.append(
                        (memory_id, array("f", vector).tobytes())
                    )
                    bucket_rows.extend(
                        (bucket, memory_id)
                        for bucket in self._bucket_ids(signature)
                    )
                placeholders = ",".join("?" for _ in ids)
                with self._conn:
                    if new_dim:
                        self._persist_dim(self._dim)
                        new_dim = False
                    self._conn.execute(
                        f"DELETE FROM buckets WHERE memory_id IN ({placeholders})",
                        tuple(ids),
                    )
                    self._conn.executemany(
                        "INSERT OR REPLACE INTO vectors (memory_id, vec) "
                        "VALUES (?, ?)",
                        vector_rows,
                    )
                    self._conn.executemany(
                        "INSERT INTO buckets (bucket, memory_id) "
                        "VALUES (?, ?)",
                        bucket_rows,
                    )
                    self._conn.commit()

    def clear(self) -> None:
        with self._lock:
            self._matrix_cache = None
            self._count = None
            self._dim = None
            self._conn.execute("DELETE FROM vectors")
            self._conn.execute("DELETE FROM buckets")
            self._conn.execute(
                "DELETE FROM meta WHERE key IN ('proj', 'dim')"
            )
            self._conn.commit()
            self._pending = 0

    def remove(self, memory_ids: list[str]) -> int:
        """Delete vectors and their bucket entries for the given memory ids.

        Idempotent: ids that are not present are simply skipped. Used by the
        engine when memories are hard-purged, so a stale vector cannot
        resurface later or waste disk space.
        """
        if not memory_ids:
            return 0
        removed = 0
        with self._lock:
            self._matrix_cache = None
            self._count = None
            for start in range(0, len(memory_ids), 500):
                chunk = memory_ids[start : start + 500]
                placeholders = ",".join("?" for _ in chunk)
                with self._conn:
                    removed += self._conn.execute(
                        f"DELETE FROM vectors WHERE memory_id IN "
                        f"({placeholders})",
                        tuple(chunk),
                    ).rowcount
                    self._conn.execute(
                        f"DELETE FROM buckets WHERE memory_id IN "
                        f"({placeholders})",
                        tuple(chunk),
                    )
        return removed

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        with self._lock:
            total = self.size
            if total == 0:
                return []
            dim = self._dimension()
            if dim is None:
                raise ValueError(
                    "vector dimension is unknown: the store is not empty "
                    "but no projection metadata exists"
                )
            if len(query_vector) != dim:
                raise ValueError(
                    f"query dimension {len(query_vector)} does not match "
                    f"index dimension {dim}"
                )
            exact_ok = (
                total <= self.full_scan_threshold
                or (
                    total <= self.exact_scan_limit
                    and total
                    * dim
                    * (4 if self._has_numpy() else 16)
                    * 1.15
                    <= self.exact_scan_max_bytes
                )
            )
            if exact_ok:
                cached = self._matrix_cache
                if (
                    cached is not None
                    and len(cached) == 4
                    and len(cached[0]) == total
                ):
                    if cached[1] is not None:
                        return self._rerank_matrix(
                            cached[0],
                            cached[1],
                            cached[2],
                            query_vector,
                            top_k,
                        )
                    return self._rerank(
                        cached[3], query_vector, top_k
                    )
                rows = self._conn.execute(
                    "SELECT memory_id, vec FROM vectors"
                ).fetchall()
                built = self._build_matrix(rows)
                self._matrix_cache = (
                    built[0], built[1], built[2], rows
                )
                if built[1] is not None:
                    return self._rerank_matrix(
                        built[0], built[1], built[2], query_vector, top_k
                    )
                return self._rerank(rows, query_vector, top_k)
            projection = self._projection()
            signature = self._signature(query_vector, projection)
            buckets: set[int] = set()
            for neighbour in self._neighbour_signatures(signature):
                buckets.update(self._bucket_ids(neighbour))
            placeholders = ",".join("?" for _ in buckets)
            rows = self._conn.execute(
                f"SELECT DISTINCT memory_id FROM buckets "
                f"WHERE bucket IN ({placeholders})",
                tuple(buckets),
            ).fetchall()
            candidate_ids = [row[0] for row in rows]
            if len(candidate_ids) > self.max_candidates:
                # Too many buckets hit: cap the candidate set instead of
                # materialising a multi-GB matrix on every query.
                candidate_ids = candidate_ids[
                    : max(self.max_candidates, top_k)
                ]
            if len(candidate_ids) < min(max(top_k * 20, 100), total):
                # Out of budget: serve the best bucket candidates instead of
                # falling back to a multi-GB full scan.
                if self.fallback_to_full_scan:
                    _LOG.warning(
                        "LSH candidates insufficient (%d) at %d vectors; "
                        "performing an exact full scan "
                        "(fallback_to_full_scan=True)",
                        len(candidate_ids),
                        total,
                    )
                    rows = self._conn.execute(
                        "SELECT memory_id, vec FROM vectors"
                    ).fetchall()
                    built = self._build_matrix(rows)
                    if built[1] is not None:
                        return self._rerank_matrix(
                            built[0],
                            built[1],
                            built[2],
                            query_vector,
                            top_k,
                        )
                    return self._rerank(rows, query_vector, top_k)
                if not candidate_ids:
                    _LOG.warning(
                        "LSH path found no candidates at %d vectors "
                        "(probe=%d); consider raising exact_scan_limit, "
                        "buckets_per_item, or enabling "
                        "fallback_to_full_scan",
                        total,
                        self.probe,
                    )
                    return []
                _LOG.warning(
                    "LSH candidates insufficient (%d/%d); returning "
                    "degraded results (enable fallback_to_full_scan or "
                    "raise exact_scan_limit for exact recall)",
                    len(candidate_ids),
                    total,
                )
                placeholders = ",".join("?" for _ in candidate_ids)
                vec_rows = self._conn.execute(
                    f"SELECT memory_id, vec FROM vectors "
                    f"WHERE memory_id IN ({placeholders})",
                    tuple(candidate_ids),
                ).fetchall()
                return self._rerank(vec_rows, query_vector, top_k)
            placeholders = ",".join("?" for _ in candidate_ids)
            vec_rows = self._conn.execute(
                f"SELECT memory_id, vec FROM vectors "
                f"WHERE memory_id IN ({placeholders})",
                tuple(candidate_ids),
            ).fetchall()
        return self._rerank(vec_rows, query_vector, top_k)

    def _rerank(
        self,
        rows: list[tuple[str, bytes]],
        query_vector: list[float],
        top_k: int,
    ) -> list[tuple[str, float]]:
        if not rows:
            return []
        ids = [row[0] for row in rows]
        dim = len(query_vector)
        try:
            import numpy as np

            payload = b"".join(row[1] for row in rows)
            n = len(rows)
            bytes_per = 4 if len(payload) == n * dim * 4 else 8
            matrix: Any = np.frombuffer(
                payload,
                dtype=np.float32 if bytes_per == 4 else np.float64,
            ).reshape(n, dim)
            if bytes_per != 4:
                matrix = matrix.astype(np.float32)
            query: Any = np.asarray(query_vector, dtype=np.float32)
            norms: Any = np.linalg.norm(matrix, axis=1)
            qnorm: float = float(np.linalg.norm(query))
            if qnorm == 0.0:
                return []
            scores: Any = matrix @ query / (norms * qnorm + 1e-9)
            order: Any = np.argsort(-scores)[:top_k]
            return [
                (ids[int(index)], float(scores[int(index)]))
                for index in order
            ]
        except ImportError:
            import heapq

            qnorm = sum(v * v for v in query_vector) ** 0.5
            if qnorm == 0.0:
                return []
            # Stream one row at a time so a huge store never materialises
            # every decoded vector as Python lists (which would blow the
            # exact-scan memory budget by 8-10x).
            best: list[tuple[float, str]] = []
            for memory_id, blob in rows:
                # New indexes store float32 blobs; legacy files are float64.
                vec = array("f" if len(blob) == dim * 4 else "d")
                vec.frombytes(blob)
                dot = sum(a * b for a, b in zip(vec, query_vector))
                norm = sum(v * v for v in vec) ** 0.5
                score = dot / (norm * qnorm + 1e-9)
                if len(best) < top_k:
                    heapq.heappush(best, (score, memory_id))
                elif score > best[0][0]:
                    heapq.heapreplace(best, (score, memory_id))
            return [
                (memory_id, score)
                for score, memory_id in sorted(best, reverse=True)
            ]

    def _build_matrix(
        self, rows: list[tuple[str, bytes]]
    ) -> tuple[list[str], Any, Any]:
        ids = [row[0] for row in rows]
        if not rows:
            return [], None, None
        try:
            import numpy as np

            payload = b"".join(row[1] for row in rows)
            dim = self._dimension() or 0
            n = len(rows)
            if dim and len(payload) == n * dim * 4:
                bytes_per = 4
            elif dim and len(payload) == n * dim * 8:
                bytes_per = 8
            else:
                raise ValueError(
                    "corrupt vector blobs: length does not match "
                    f"{n} rows x {dim} dims"
                )
            matrix: Any = np.frombuffer(
                payload,
                dtype=np.float32 if bytes_per == 4 else np.float64,
            ).reshape(n, dim)
            if bytes_per != 4:
                matrix = matrix.astype(np.float32)
            norms: Any = np.linalg.norm(matrix, axis=1)
            return ids, matrix, norms
        except ImportError:
            return ids, None, None

    def _rerank_matrix(
        self,
        ids: list[str],
        matrix: Any,
        norms: Any,
        query_vector: list[float],
        top_k: int,
    ) -> list[tuple[str, float]]:
        import numpy as np

        query = np.asarray(query_vector, dtype=np.float32)
        qnorm = float(np.linalg.norm(query))
        if qnorm == 0.0:
            return []
        scores = matrix @ query / (norms * qnorm + 1e-9)
        order = np.argsort(-scores)[:top_k]
        return [
            (ids[int(index)], float(scores[int(index)]))
            for index in order
        ]

    def flush(self) -> None:
        with self._lock:
            if self._pending:
                self._conn.commit()
                self._pending = 0

    def close(self) -> None:
        self.flush()
        self._conn.close()

    def __enter__(self) -> VectorIndex:  # noqa: PYI034 (3.10 CI)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def size(self) -> int:
        if self._count is None:
            row = self._conn.execute(
                "SELECT COUNT(*) FROM vectors"
            ).fetchone()
            self._count = int(row[0])
        return self._count

    def has(self, memory_id: str) -> bool:
        """Whether a vector already exists for this memory id."""
        row = self._conn.execute(
            "SELECT 1 FROM vectors WHERE memory_id = ?", (memory_id,)
        ).fetchone()
        return row is not None


__all__ = ["VectorIndex"]
