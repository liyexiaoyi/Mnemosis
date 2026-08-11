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
import json
import math
import operator
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from collections.abc import Callable


class EmbeddingAPIError(RuntimeError):
    """External embedding API call failed (auth, quota, network, ...)."""


class Embedder:
    """Protocol-ish base: `embed(text) -> list[float]` + cosine."""

    cache_key: str = ""

    def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts; external APIs override with one call."""
        return [self.embed(text) for text in texts]

    @staticmethod
    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(map(operator.mul, a, b))
        norm_a = math.sqrt(sum(map(operator.mul, a, a)))
        norm_b = math.sqrt(sum(map(operator.mul, b, b)))
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


class CallableEmbedder(Embedder):
    """Wrap any external embedding function, e.g. an OpenAI-compatible API."""

    def __init__(
        self,
        fn: Callable[[str], list[float]],
        fn_many: Callable[[list[str]], list[list[float]]] | None = None,
    ) -> None:
        self.fn = fn
        self.fn_many = fn_many

    def embed(self, text: str) -> list[float]:
        return self.fn(text)

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        if self.fn_many is None:
            return [self.fn(text) for text in texts]
        return self.fn_many(texts)


def _post_json(
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout: float,
    retries: int = 3,
) -> dict:
    """POST JSON with exponential backoff on 429/5xx and network errors."""
    for attempt in range(retries):
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if (
                exc.code in (429, 500, 502, 503, 504)
                and attempt < retries - 1
            ):
                time.sleep(1.0 * (2**attempt))
                continue
            body = exc.read().decode("utf-8", "ignore")[:300]
            raise EmbeddingAPIError(
                f"embedding API HTTP {exc.code}: {body or exc.reason}"
            ) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            if attempt < retries - 1:
                time.sleep(1.0 * (2**attempt))
                continue
            raise EmbeddingAPIError(
                f"embedding API unreachable: {exc}"
            ) from exc
    raise EmbeddingAPIError("embedding API retries exhausted")


def _chunk_texts(
    texts: list[str], max_chars: int = 6000, max_items: int = 100
) -> list[list[str]]:
    """Chunk by estimated size so batch calls stay under model limits."""
    chunks: list[list[str]] = []
    current: list[str] = []
    current_chars = 0
    for text in texts:
        if current and (
            len(current) >= max_items
            or current_chars + len(text) > max_chars
        ):
            chunks.append(current)
            current = []
            current_chars = 0
        current.append(text)
        current_chars += len(text)
    if current:
        chunks.append(current)
    return chunks


def ollama_embedder(
    model: str = "nomic-embed-text",
    base_url: str = "http://127.0.0.1:11434",
    timeout: float = 60.0,
) -> Embedder:
    """Embedder backed by a local Ollama ``/api/embed`` endpoint."""
    url = base_url.rstrip("/") + "/api/embed"

    def _embed(text: str) -> list[float]:
        payload = {"model": model, "input": [text]}
        data = _post_json(
            url, payload, {"Content-Type": "application/json"}, timeout
        )
        return [float(x) for x in data["embeddings"][0]]

    def _embed_many(texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for chunk in _chunk_texts(texts):
            payload = {"model": model, "input": chunk}
            data = _post_json(
                url, payload, {"Content-Type": "application/json"}, timeout
            )
            rows = data["embeddings"]
            if len(rows) != len(chunk):
                raise EmbeddingAPIError(
                    f"ollama returned {len(rows)} embeddings for "
                    f"{len(chunk)} inputs"
                )
            vectors.extend([float(x) for x in row] for row in rows)
        return vectors

    return CallableEmbedder(_embed, _embed_many)


def openai_embedder(
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    timeout: float = 60.0,
) -> Embedder:
    """OpenAI-compatible embeddings endpoint (DashScope, OpenAI, etc.)."""
    model = (
        model
        or os.environ.get("MNEMOSIS_EMBEDDING_MODEL")
        or "text-embedding-v3"
    )
    base_url = (
        base_url
        or os.environ.get("MNEMOSIS_EMBEDDING_BASE_URL")
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    api_key = api_key or os.environ.get("MNEMOSIS_EMBEDDING_API_KEY")
    if not api_key:
        raise ValueError(
            "openai embedder needs MNEMOSIS_EMBEDDING_API_KEY or api_key=..."
        )
    url = base_url.rstrip("/") + "/embeddings"

    def _embed(text: str) -> list[float]:
        payload = {"model": model, "input": text}
        data = _post_json(
            url,
            payload,
            {
                "Content-Type": "application/json",
                "Authorization": "Bearer " + api_key,
            },
            timeout,
        )
        return [float(x) for x in data["data"][0]["embedding"]]

    def _embed_many(texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for chunk in _chunk_texts(texts):
            payload = {"model": model, "input": chunk}
            data = _post_json(
                url,
                payload,
                {
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + api_key,
                },
                timeout,
            )
            ordered = sorted(data["data"], key=lambda row: row["index"])
            if len(ordered) != len(chunk):
                raise EmbeddingAPIError(
                    f"openai returned {len(ordered)} embeddings for "
                    f"{len(chunk)} inputs"
                )
            vectors.extend(
                [float(x) for x in row["embedding"]] for row in ordered
            )
        return vectors

    return CallableEmbedder(_embed, _embed_many)


def make_embedder(
    provider: str | None,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    cache_path: str | None = None,
    timeout: float = 60.0,
) -> Embedder | None:
    """Build an embedder by provider; ``None``/``"none"`` disables dense recall."""
    if not provider or provider == "none":
        return None
    if provider == "ollama":
        embedder = ollama_embedder(
            model or "nomic-embed-text",
            base_url or "http://127.0.0.1:11434",
            timeout,
        )
    elif provider == "openai":
        embedder = openai_embedder(model, base_url, api_key, timeout)
    else:
        raise ValueError(
            f"unknown embedder provider: {provider!r} (none|ollama|openai)"
        )
    if cache_path:
        from .embedding_cache import SqliteEmbeddingCache  # lazy: avoid cycle

        return SqliteEmbeddingCache(embedder, cache_path)
    return embedder


__all__ = [
    "CallableEmbedder",
    "Embedder",
    "EmbeddingAPIError",
    "NGramEmbedder",
    "make_embedder",
    "ollama_embedder",
    "openai_embedder",
]
