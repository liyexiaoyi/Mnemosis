"""Zero-dependency embedding for semantic recall.

The default `NGramEmbedder` is a deterministic feature-hashing embedder over
character n-grams (distributional similarity; Harris, 1954). It makes recall
tolerant to synonyms and spelling variants ("prefer" ~ "preference",
"color" ~ "colour", "中文" ~ "中文技术") without any model or network.

Any external embedder (e.g. an OpenAI-compatible API) can be wrapped with
`CallableEmbedder` and passed to `MemoryEngine(embedder=...)`.
"""

from __future__ import annotations

import hashlib
import math
import re
from collections import Counter
from typing import Callable


class Embedder:
    """Protocol-ish base: `embed(text) -> list[float]` + cosine."""

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    @staticmethod
    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(y * y for y in b))
        if norm_a == 0.0 or norm_b == 0.0:
            return 0.0
        return dot / (norm_a * norm_b)


class NGramEmbedder(Embedder):
    """Deterministic hashed character n-gram embeddings (no dependencies)."""

    def __init__(
        self,
        dimension: int = 256,
        min_ngram: int = 2,
        max_ngram: int = 4,
    ) -> None:
        self.dimension = dimension
        self.min_ngram = min_ngram
        self.max_ngram = max_ngram

    def _ngrams(self, token: str, lo: int | None = None, hi: int | None = None) -> list[str]:
        lo = lo or self.min_ngram
        hi = hi or self.max_ngram
        length = len(token)
        if length < lo:
            return [token] if token else []
        return [
            token[i : i + size]
            for size in range(lo, min(hi, length) + 1)
            for i in range(length - size + 1)
        ]

    def features(self, text: str) -> list[str]:
        lowered = text.lower()
        words = [w for w in re.findall(r"[a-z0-9]+", lowered) if len(w) >= 2]
        cjk = re.findall(r"[\u4e00-\u9fff]", lowered)
        features: list[str] = []
        for word in words:
            features.append(word)
            features.extend(self._ngrams(word))
        if cjk:
            features.extend(cjk)  # single characters
            features.extend(self._ngrams("".join(cjk), lo=2, hi=2))  # bigrams
        return features

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimension
        for feature, count in Counter(self.features(text)).items():
            digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest[:4], "little") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            return vector
        return [v / norm for v in vector]


class CallableEmbedder(Embedder):
    """Wrap any external embedding function, e.g. an OpenAI-compatible API."""

    def __init__(self, fn: Callable[[str], list[float]]) -> None:
        self.fn = fn

    def embed(self, text: str) -> list[float]:
        return self.fn(text)


__all__ = ["CallableEmbedder", "Embedder", "NGramEmbedder"]

