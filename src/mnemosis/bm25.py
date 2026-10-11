"""Read-only BM25 cue discovery with cached term-frequency postings.

The index is a disposable lexical cache, never evidence or learned state.
BM25 scores express relevance, not confidence or factual correctness.
"""
from __future__ import annotations

import heapq
import math
from importlib import import_module
from collections import Counter, defaultdict

from .types import MemoryStatus, RecallResult, tokenize


class BM25Index:
    backend_name = "python"

    def __init__(self, items, k1=1.5, b=0.75):
        self.k1, self.b = k1, b
        self.lengths = {}
        self.order = {}
        self.postings = defaultdict(dict)
        self.terms = {}
        self.total_length = 0
        self.n = 0
        self.avg_length = 0.0
        for item in items:
            self.upsert(item)

    def remove(self, ident):
        if ident not in self.lengths:
            return
        self.total_length -= self.lengths.pop(ident)
        self.order.pop(ident)
        for term in self.terms.pop(ident):
            posting = self.postings[term]
            posting.pop(ident)
            if not posting:
                del self.postings[term]
        self.n = len(self.lengths)
        self.avg_length = self.total_length / max(1, self.n)

    def upsert(self, item):
        self.remove(item.id)
        counts = Counter(tokenize(item.content) + list(item.cues))
        length = sum(counts.values())
        self.lengths[item.id] = length
        self.total_length += length
        self.order[item.id] = item.seq
        self.terms[item.id] = tuple(counts)
        for term, count in counts.items():
            self.postings[term][item.id] = count
        self.n = len(self.lengths)
        self.avg_length = self.total_length / max(1, self.n)

    def search(self, query, top_k, excluded):
        scores = defaultdict(float)
        for term in sorted(set(tokenize(query))):
            posting = self.postings.get(term, {})
            df = len(posting)
            idf = math.log1p((self.n - df + 0.5)/(df + 0.5))
            for ident, tf in posting.items():
                if ident in excluded:
                    continue
                length = self.lengths[ident]
                norm = self.k1 * (1 - self.b + self.b * length/max(self.avg_length, 1e-12))
                scores[ident] += idf * tf * (self.k1 + 1)/(tf + norm)
        return heapq.nsmallest(top_k, scores.items(),
                              key=lambda row: (-row[1], self.order[row[0]], row[0]))


class RustBM25Index:
    """Optional resident scoring kernel; all tokenization stays in Python."""
    backend_name = "rust"

    def __init__(self, items, k1=1.5, b=0.75):
        try:
            native = import_module("_mnemosis_rust")
        except ImportError as exc:
            raise ImportError("Rust BM25 extension unavailable; install mnemosis-bm25-native "
                              "or set bm25_backend='python'") from exc
        if getattr(native, "API_VERSION", None) != 1:
            raise ImportError("Rust BM25 extension incompatible; reinstall mnemosis-bm25-native "
                              "or set bm25_backend='python'")
        self.kernel = native.BM25Kernel(k1, b)
        self.build_profile = native.BUILD_PROFILE
        batch = []
        for item in items:
            batch.append(self._record(item))
            if len(batch) == 1024:
                self.kernel.upsert_batch(batch)
                batch.clear()
        if batch:
            self.kernel.upsert_batch(batch)

    @staticmethod
    def _record(item):
        return (item.id, item.seq, dict(Counter(tokenize(item.content) + list(item.cues))))

    def remove(self, ident):
        self.remove_batch([ident])

    def remove_batch(self, ids):
        self.kernel.remove_batch(list(ids))

    def upsert(self, item):
        self.upsert_batch([item])

    def upsert_batch(self, items):
        self.kernel.upsert_batch([self._record(item) for item in items])

    def search(self, query, top_k, excluded):
        if top_k <= 0:
            return []
        return self.kernel.search(sorted(set(tokenize(query))), top_k, set(excluded))


def recall_bm25(engine, query, *, kind=None, top_k=5, exclude_ids=None):
    """Find lexical candidates without rehearsal, log updates or new links.

    Cold queries build an index; known changes update it incrementally. Only
    one corpus/kind is cached, bounding duplicate index storage. Callers
    needing familiarity reinforcement use the fused retrieval entry point.
    """
    if top_k <= 0 or not query.strip():
        return []
    with engine._lock:
        implementation = getattr(engine, "bm25_backend", "python")
        if implementation not in ("python", "rust"):
            raise ValueError("bm25_backend must be 'python' or 'rust'")
        index_type = RustBM25Index if implementation == "rust" else BM25Index
        token = engine.backend.revision_token()
        cached = getattr(engine, "_bm25_cache", None)
        if cached is not None and cached[2].backend_name != implementation:
            cached = None
        if token is not None and cached is not None and cached[:2] == (kind, token):
            index = cached[2]
        else:
            changes = None
            if token is not None and cached is not None and cached[0] == kind:
                changes = engine.backend.lexical_changes_since(cached[1])
            # Never leave a partially mutated index reachable under an old
            # token if a backend read or tokenization raises an exception.
            engine._bm25_cache = None
            if changes is not None:
                index = cached[2]
                if implementation == "rust":
                    index.remove_batch(changes)
                    index.upsert_batch(item for item in engine.backend.get_many(changes)
                                       if item.status is MemoryStatus.ACTIVE
                                       and (kind is None or item.kind == kind))
                else:
                    for ident in changes:
                        index.remove(ident)
                    for item in engine.backend.get_many(changes):
                        if item.status is MemoryStatus.ACTIVE and (kind is None or item.kind == kind):
                            index.upsert(item)
            else:
                index = index_type(engine.store.all_active(kind=kind))
            if token is not None and engine.backend.revision_token() == token:
                engine._bm25_cache = (kind, token, index)
        excluded = set(exclude_ids or ()) | set(engine._suppressed_ids)
        ranked = index.search(query, top_k, excluded)
        fresh = {item.id: item for item in engine.backend.get_many(ident for ident, _ in ranked)}
        return [RecallResult(item=fresh[ident], score=score,
                             reasons=[f"bm25 cue relevance {score:.4f}"], confident=False)
                for ident, score in ranked
                if ident in fresh and fresh[ident].status is MemoryStatus.ACTIVE
                and (kind is None or fresh[ident].kind == kind)
                and ident not in engine._suppressed_ids]
