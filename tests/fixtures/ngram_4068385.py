"""Frozen NGramEmbedder from commit4068385; compatibility oracle, never optimized."""
from __future__ import annotations
import hashlib,math,operator,re
from collections import Counter
from mnemosis.embedding import Embedder

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
        words = [
            w
            for w in re.findall(r"[a-z0-9\u00e0-\u024f]+", lowered)
            if len(w) >= 2
        ]
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

    @staticmethod
    def cosine(a: list[float], b: list[float]) -> float:
        """Fast path: both vectors are unit-normalized, so cosine == dot."""
        return sum(map(operator.mul, a, b))
