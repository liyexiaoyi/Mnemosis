"""Vector-index sync: update refreshes, purge cleans, dense recall skips recycled."""

from __future__ import annotations

import unittest

from mnemosis import MemoryEngine
from mnemosis.embedding import Embedder
from mnemosis.types import MemoryKind, MemoryStatus, SourceRecord, SourceType
from mnemosis.vector_index import VectorIndex


class _AlphaBetaEmbedder(Embedder):
    """Deterministic 2-d embedder separating alpha / beta content."""

    def embed(self, text: str) -> list[float]:
        if "alpha" in text:
            return [1.0, 0.0]
        return [0.0, 1.0]


class _CountingEmbedder(Embedder):
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, text: str) -> list[float]:
        self.calls += 1
        if "alpha" in text:
            return [1.0, 0.0]
        if "beta" in text:
            return [0.0, 1.0]
        return [0.5, 0.5]


class VectorSyncTests(unittest.TestCase):
    def _engine(self, embedder: Embedder) -> MemoryEngine:
        return MemoryEngine(
            embedder=embedder,
            index_embedder=embedder,
            vector_index=VectorIndex(dim=2),
        )

    def test_update_refreshes_stored_vector(self) -> None:
        embedder = _AlphaBetaEmbedder()
        engine = self._engine(embedder)
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha topic one",
            kind=MemoryKind.SEMANTIC,
            source=source,
            auto_cues=False,
        )
        self.assertTrue(engine.vector_index.has(item.id))
        engine.update(item.id, content="beta topic two")
        self.assertTrue(engine.vector_index.has(item.id))
        hits = engine.vector_index.search([0.0, 1.0], top_k=3)
        self.assertEqual(hits[0][0], item.id)

    def test_update_without_content_change_does_not_reembed(self) -> None:
        counting = _CountingEmbedder()
        engine = self._engine(counting)
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha record",
            kind=MemoryKind.SEMANTIC,
            source=source,
            auto_cues=False,
        )
        calls_after_remember = counting.calls
        engine.update(item.id, importance=0.9)
        self.assertEqual(counting.calls, calls_after_remember)

    def test_purge_removes_vectors_for_purged_memories(self) -> None:
        embedder = _AlphaBetaEmbedder()
        engine = self._engine(embedder)
        source = SourceRecord(origin=SourceType.USER)
        doomed = engine.remember(
            "alpha doomed",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        kept = engine.remember(
            "beta kept",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        engine.forget(doomed.id)
        engine.purge()
        self.assertFalse(engine.vector_index.has(doomed.id))
        self.assertTrue(engine.vector_index.has(kept.id))

    def test_forget_removes_vector_and_restore_reembeds(self) -> None:
        embedder = _AlphaBetaEmbedder()
        engine = self._engine(embedder)
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha roundtrip",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        self.assertTrue(engine.vector_index.has(item.id))
        engine.forget(item.id)
        self.assertFalse(engine.vector_index.has(item.id))
        engine.restore(item.id)
        self.assertTrue(engine.vector_index.has(item.id))
        hits = engine.vector_index.search([1.0, 0.0], top_k=3)
        self.assertEqual(hits[0][0], item.id)

    def test_purge_preserves_restored_memory(self) -> None:
        embedder = _AlphaBetaEmbedder()
        engine = self._engine(embedder)
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha restored before purge",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        engine.forget(item.id)
        engine.restore(item.id)
        self.assertEqual(engine.purge(), 0)
        self.assertTrue(engine.vector_index.has(item.id))
        self.assertIs(
            engine.store.backend.get(item.id).status, MemoryStatus.ACTIVE
        )

    def test_purge_preserves_restored_memory_sqlite(self) -> None:
        embedder = _AlphaBetaEmbedder()
        engine = MemoryEngine(
            ":memory:",
            embedder=embedder,
            index_embedder=embedder,
            vector_index=VectorIndex(dim=2),
        )
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha sqlite restored before purge",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        engine.forget(item.id)
        engine.restore(item.id)
        self.assertEqual(engine.purge(), 0)
        self.assertIs(
            engine.store.backend.get(item.id).status, MemoryStatus.ACTIVE
        )
        self.assertTrue(engine.vector_index.has(item.id))

    def test_recycled_ids_paginates(self) -> None:
        engine = MemoryEngine(":memory:")
        source = SourceRecord(origin=SourceType.USER)
        ids = [
            engine.remember(
                f"recycled item {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                auto_cues=False,
            ).id
            for index in range(3)
        ]
        for memory_id in ids:
            engine.forget(memory_id)
        page1 = engine.backend.recycled_ids(limit=2, after_seq=-1)
        page2 = engine.backend.recycled_ids(
            limit=2, after_seq=page1[-1][0]
        )
        self.assertEqual(len(page1), 2)
        self.assertEqual(len(page2), 1)
        self.assertEqual(
            {memory_id for _, memory_id in page1}
            | {memory_id for _, memory_id in page2},
            set(ids),
        )

    def test_delete_if_recycled_skips_restored(self) -> None:
        engine = MemoryEngine(":memory:")
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha conditional delete",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        engine.forget(item.id)
        engine.restore(item.id)
        self.assertFalse(engine.backend.delete_if_recycled(item.id))
        self.assertIsNotNone(engine.backend.get(item.id))

    def test_sleep_cleans_vectors_of_recycled_memories(self) -> None:
        embedder = _AlphaBetaEmbedder()
        engine = self._engine(embedder)
        source = SourceRecord(origin=SourceType.USER)
        doomed = engine.remember(
            "alpha sleep doomed",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        kept = engine.remember(
            "beta sleep kept fact",
            kind=MemoryKind.SEMANTIC,
            source=source,
            importance=0.9,
            auto_cues=False,
        )
        engine.forget(doomed.id)
        engine.sleep()
        self.assertFalse(engine.vector_index.has(doomed.id))
        self.assertTrue(engine.vector_index.has(kept.id))

    def test_update_on_recycled_memory_does_not_reembed(self) -> None:
        counting = _CountingEmbedder()
        engine = self._engine(counting)
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha recycled update",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        engine.forget(item.id)
        calls_after_forget = counting.calls
        engine.update(item.id, content="beta recycled update")
        self.assertEqual(counting.calls, calls_after_forget)
        self.assertFalse(engine.vector_index.has(item.id))

    def test_fused_dense_recall_skips_recycled_memories(self) -> None:
        embedder = _AlphaBetaEmbedder()
        engine = self._engine(embedder)
        source = SourceRecord(origin=SourceType.USER)
        item = engine.remember(
            "alpha unique marker",
            kind=MemoryKind.SEMANTIC,
            source=source,
            auto_cues=False,
        )
        engine.forget(item.id)
        results = engine.recall_fused(
            "alpha unique marker",
            top_k=5,
            dense_embedder=embedder,
            vector_index=engine.vector_index,
        )
        self.assertNotIn(item.id, {result.item.id for result in results})


if __name__ == "__main__":
    unittest.main()
