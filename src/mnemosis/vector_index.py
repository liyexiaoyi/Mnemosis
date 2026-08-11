"""Zero-dependency IVF-style vector index (LSH buckets + cosine rerank).

Motivation: dense recall in :mod:`mnemosis.hybrid` used to scan every active
memory and embed/score them at query time. This module moves the work to
write time: vectors are persisted in SQLite and each memory is hashed into a
few LSH buckets (random hyperplane projections, Charikar 2002-style). A query
only visits its own buckets (plus single-bit Hamming neighbours), then
re-ranks the candidates with exact cosine similarity. numpy is optional; the
fallback is pure Python.
"""

from __future__ import annotations

import os
import random
import sqlite3
import struct
import threading
from array import array


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
        max_candidates: int = 30000,
    ) -> None:
        self.path = path or ":memory:"
        self.bits = bits
        self.buckets_per_item = buckets_per_item
        self.seed = seed
        self.probe = probe
        self.full_scan_threshold = full_scan_threshold
        self.max_candidates = max_candidates
        self._dim = dim
        self._lock = threading.Lock()
        self._pending = 0
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
                flat[i * dim : (i + 1) * dim]
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
        if self._dim is None:
            self._dim = len(vector)
        with self._lock:
            projection = self._projection()
            signature = self._signature(vector, projection)
            self._conn.execute(
                "INSERT OR REPLACE INTO vectors (memory_id, vec) VALUES (?, ?)",
                (memory_id, array("d", vector).tobytes()),
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

    def clear(self) -> None:
        with self._lock:
            self._conn.execute("DELETE FROM vectors")
            self._conn.execute("DELETE FROM buckets")
            self._conn.execute("DELETE FROM meta WHERE key='proj'")
            self._conn.commit()
            self._pending = 0

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 10,
    ) -> list[tuple[str, float]]:
        with self._lock:
            total = self.size
            if total <= self.full_scan_threshold:
                rows = self._conn.execute(
                    "SELECT memory_id, vec FROM vectors"
                ).fetchall()
                return self._rerank(rows, query_vector, top_k)
            projection = self._projection()
            signature = self._signature(query_vector, projection)
            buckets: set[int] = set()
            for signature in self._neighbour_signatures(signature):
                buckets.update(self._bucket_ids(signature))
            placeholders = ",".join("?" for _ in buckets)
            rows = self._conn.execute(
                f"SELECT DISTINCT memory_id FROM buckets "
                f"WHERE bucket IN ({placeholders})",
                tuple(buckets),
            ).fetchall()
            candidate_ids = [row[0] for row in rows]
            if len(candidate_ids) > self.max_candidates:
                # Too many buckets hit: brute-force rerank is faster than a
                # gigantic IN(...) query.
                rows = self._conn.execute(
                    "SELECT memory_id, vec FROM vectors"
                ).fetchall()
                return self._rerank(rows, query_vector, top_k)
            if len(candidate_ids) < min(top_k * 5, total):
                # LSH missed too much: fall back to a full scan.
                rows = self._conn.execute(
                    "SELECT memory_id, vec FROM vectors"
                ).fetchall()
                return self._rerank(rows, query_vector, top_k)
            if not candidate_ids:
                return []
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
            import numpy as np  # noqa: PLC0415

            payload = b"".join(row[1] for row in rows)
            matrix = np.frombuffer(payload, dtype=np.float64).reshape(
                len(rows), dim
            ).astype(np.float32)
            query = np.asarray(query_vector, dtype=np.float32)
            norms = np.linalg.norm(matrix, axis=1)
            qnorm = float(np.linalg.norm(query))
            if qnorm == 0.0:
                return []
            scores = matrix @ query / (norms * qnorm + 1e-9)
            order = np.argsort(-scores)[:top_k]
            return [
                (ids[int(index)], float(scores[int(index)]))
                for index in order
            ]
        except ImportError:
            vectors = []
            for row in rows:
                vec = array("d")
                vec.frombytes(row[1])
                vectors.append(vec.tolist())
            qnorm = sum(v * v for v in query_vector) ** 0.5
            if qnorm == 0.0:
                return []
            scored = []
            for memory_id, vector in zip(ids, vectors):
                dot = sum(a * b for a, b in zip(vector, query_vector))
                norm = sum(v * v for v in vector) ** 0.5
                scored.append((memory_id, dot / (norm * qnorm + 1e-9)))
            scored.sort(key=lambda row: -row[1])
            return scored[:top_k]

    def flush(self) -> None:
        with self._lock:
            if self._pending:
                self._conn.commit()
                self._pending = 0

    def close(self) -> None:
        self.flush()
        self._conn.close()

    def __enter__(self) -> "VectorIndex":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @property
    def size(self) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) FROM vectors"
        ).fetchone()
        return int(row[0])


__all__ = ["VectorIndex"]
