"""Pure embedding kNN baseline (naive vector-store RAG, no memory logic)."""

from __future__ import annotations

from bench_utils import pin_local_src

pin_local_src()

from mnemosis.embedding import Embedder, NGramEmbedder


class EmbeddingBaseline:
    def __init__(
        self,
        items: list[dict],
        embedder: Embedder | None = None,
    ) -> None:
        self.items = items
        self.embedder = embedder or NGramEmbedder()
        self.vectors = [
            self.embedder.embed(item["content"]) for item in items
        ]

    def search(self, query: str, top_k: int = 5) -> list[tuple[str, float]]:
        query_vector = self.embedder.embed(query)
        scored = sorted(
            (
                (self.items[i]["content"], self.embedder.cosine(query_vector, v))
                for i, v in enumerate(self.vectors)
            ),
            key=lambda pair: pair[1],
            reverse=True,
        )
        return scored[:top_k]

