"""Synonym-tolerant recall: keyword-only vs n-gram embeddings."""

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def main() -> None:
    user = SourceRecord(origin=SourceType.USER)
    keyword_only = MemoryEngine()
    semantic = MemoryEngine(embedder=NGramEmbedder())

    for engine in (keyword_only, semantic):
        engine.remember(
            "The user prefers Chinese for technical discussions.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["user", "language"],
            importance=0.8,
        )

    query = "the user's preference in technical talks"
    for name, engine in (("keyword-only", keyword_only), ("+ ngram embedder", semantic)):
        print(f"== {name} ==")
        for result in engine.recall(query, top_k=3):
            print(f"  {result.score:.3f}  {result.item.content}")
            print(f"        reasons: {result.reasons}")


if __name__ == "__main__":
    main()

