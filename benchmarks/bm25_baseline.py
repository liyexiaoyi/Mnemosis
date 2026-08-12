"""Minimal BM25 retrieval baseline.

Used to compare Mnemosis against the retrieval mechanism used by projects
like hippo-memory (BM25 + cosine). BM25 is a strong, classic lexical ranker;
it has no decay, no importance, no associations, no source monitoring.
"""

from __future__ import annotations

import math
from collections import Counter

from bench_utils import pin_local_src

pin_local_src()

from mnemosis.types import tokenize


class Bm25Index:
    def __init__(
        self,
        items: list[dict],
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.items = items
        self.k1 = k1
        self.b = b
        self.doc_terms = [
            tokenize(item["content"]) + [c for c in item.get("cues", [])]
            for item in items
        ]
        self.doc_freqs: Counter[str] = Counter()
        for terms in self.doc_terms:
            for term in set(terms):
                self.doc_freqs[term] += 1
        self.doc_len = [len(terms) for terms in self.doc_terms]
        self.avg_dl = sum(self.doc_len) / max(1, len(self.doc_len))
        self.n_docs = len(items)

    def _idf(self, term: str) -> float:
        df = self.doc_freqs.get(term, 0)
        return math.log(1 + (self.n_docs - df + 0.5) / (df + 0.5))

    def score(self, query: str, doc_index: int) -> float:
        query_terms = set(tokenize(query))
        counts = Counter(self.doc_terms[doc_index])
        dl = self.doc_len[doc_index]
        total = 0.0
        for term in query_terms:
            tf = counts.get(term, 0)
            if tf == 0:
                continue
            denom = tf + self.k1 * (1 - self.b + self.b * dl / self.avg_dl)
            total += self._idf(term) * (tf * (self.k1 + 1)) / denom
        return total

    def recall(self, query: str, top_k: int = 5) -> list[str]:
        scored = sorted(
            range(self.n_docs),
            key=lambda idx: self.score(query, idx),
            reverse=True,
        )
        return [self.items[idx]["content"] for idx in scored[:top_k]]

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        scored = sorted(
            range(self.n_docs),
            key=lambda idx: self.score(query, idx),
            reverse=True,
        )
        return [
            (self.items[idx]["content"], self.score(query, idx))
            for idx in scored[:top_k]
        ]
