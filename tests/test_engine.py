import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.embedding import Embedder, EmbeddingAPIError
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow
from mnemosis.vector_index import VectorIndex


class _BatchCountingEmbedder(Embedder):
    def __init__(self) -> None:
        self.calls = 0
        self.batches: list[list[str]] = []

    def embed(self, text: str) -> list[float]:
        return [1.0, 0.0, 0.0]

    def embed_many(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        self.batches.append(list(texts))
        return [[1.0, 0.0, 0.0] for _ in texts]


class MemoryEngineTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()

    def source(self, origin=SourceType.USER):
        return SourceRecord(origin=origin)

    def test_remember_recall_english(self):
        self.engine.remember(
            "The user prefers Chinese for technical discussions.",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
            cues=["user", "language", "preference"],
            importance=0.9,
        )
        results = self.engine.recall("what language does the user prefer?", top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0].item.kind, MemoryKind.SEMANTIC)
        self.assertGreater(results[0].score, 0.0)
        self.assertIn("overlap", results[0].reasons[0])

    def test_remember_recall_chinese(self):
        self.engine.remember(
            "用户喜欢在技术讨论中使用中文。",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
            cues=["用户", "语言", "偏好"],
            importance=0.9,
        )
        results = self.engine.recall("用户偏好什么语言？", top_k=3)
        self.assertTrue(results)
        self.assertGreater(results[0].score, 0.0)

    def test_semantic_dedupe_by_content_hash(self):
        first = self.engine.remember(
            "The user is a Python developer.",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
            importance=0.5,
        )
        second = self.engine.remember(
            "The user is a Python developer.",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
            importance=0.9,
        )
        self.assertEqual(first.id, second.id)
        stats = self.engine.stats()
        self.assertEqual(stats["semantic"], 1)
        self.assertAlmostEqual(second.importance, 0.9)

    def test_tracks_are_separate(self):
        self.engine.remember(
            "We fixed the bug yesterday.",
            kind=MemoryKind.EPISODIC,
            source=self.source(),
        )
        self.engine.remember(
            "SQLite is used for persistence.",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
        )
        stats = self.engine.stats()
        self.assertEqual(stats["episodic"], 1)
        self.assertEqual(stats["semantic"], 1)

    def test_recall_reinforces_access(self):
        item = self.engine.remember(
            "Remember to review the design doc.",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
            cues=["design", "review"],
        )
        access_before = item.access_count
        self.engine.recall("review the design doc", top_k=1)
        refreshed = self.engine.backend.get(item.id)
        self.assertGreater(refreshed.access_count, access_before)
        self.assertGreaterEqual(refreshed.strength, 1.0)

    def test_sleep_promotes_episodic_to_semantic(self):
        now = utcnow()
        item = self.engine.remember(
            "Yesterday we debugged the SQLite locking issue together.",
            kind=MemoryKind.EPISODIC,
            source=self.source(SourceType.AGENT),
            cues=["sqlite", "debug"],
            created_at=now - timedelta(days=2),
        )
        for _ in range(3):
            self.engine.recall("sqlite locking debug", top_k=1)
        report = self.engine.sleep(now=now)
        self.assertEqual(len(report.promoted), 1)
        stats = self.engine.stats()
        self.assertEqual(stats["semantic"], 1)
        semantic = self.engine.store.all_active(MemoryKind.SEMANTIC)[0]
        self.assertIn("sqlite", semantic.cues)
        self.assertEqual(len(self.engine.related(item.id)), 1)

    def test_sleep_detects_conflicts(self):
        self.engine.remember(
            "The project deadline is Friday.",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
            cues=["project", "deadline"],
            confidence=0.9,
        )
        self.engine.remember(
            "The project deadline is Monday.",
            kind=MemoryKind.SEMANTIC,
            source=self.source(),
            cues=["project", "deadline"],
            confidence=0.9,
        )
        report = self.engine.sleep()
        self.assertEqual(len(report.conflicts), 1)
        self.assertEqual(len(self.engine.meta.contradictions()), 1)

    def test_recycle_flow(self):
        item = self.engine.remember(
            "Old unimportant note.",
            kind=MemoryKind.EPISODIC,
            source=self.source(),
            importance=0.1,
        )
        self.assertTrue(self.engine.forget(item.id))
        self.assertEqual(self.engine.recall("old unimportant note", top_k=5), [])
        self.assertTrue(self.engine.restore(item.id))
        self.assertGreaterEqual(len(self.engine.recall("old unimportant note", top_k=5)), 1)
        self.engine.forget(item.id)
        self.assertEqual(self.engine.purge(), 1)
        self.assertIsNone(self.engine.backend.get(item.id))

    def test_recycled_memories_do_not_surface_in_anchor_candidates(self):
        """Anchor candidate lookup must never return soft-deleted rows."""
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        recycled = engine.remember(
            "寄养店电话 400-777-8888。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=["寄养店"],
            auto_cues=False,
        )
        engine.forget(recycled.id)
        candidates = engine._anchor_items({"寄养店", "电话"}, None, set())
        self.assertNotIn(
            recycled.id, {candidate.id for candidate in candidates}
        )
        active = engine.remember(
            "健身房电话 555-0100。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=["健身房"],
            auto_cues=False,
        )
        candidates2 = engine._anchor_items({"健身房", "电话"}, None, set())
        self.assertIn(active.id, {candidate.id for candidate in candidates2})

    def test_remember_many_batches_unique_seq_and_searchable_terms(self):
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        records = [
            {
                "content": f"批量记忆 {index} 主题A",
                "kind": MemoryKind.EPISODIC,
                "source": source,
            }
            for index in range(50)
        ]
        stored = engine.remember_many(records)
        self.assertEqual(len(stored), 50)
        seqs = [item.seq for item in stored]
        self.assertEqual(len(set(seqs)), 50)
        ids = engine.backend.find_by_terms({"批量"}, None)
        self.assertEqual(len(ids), 50)
        results = engine.recall("批量记忆 17", top_k=3)
        self.assertEqual(results[0].item.content, "批量记忆 17 主题A")

    def test_import_memories_builds_term_index(self):
        """Imported rows must be reachable through the term index."""
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        payload = {
            "memories": [
                {
                    "content": "imported 独特词",
                    "kind": "episodic",
                    "source": user.to_dict(),
                    "cues": ["导入测试"],
                }
            ]
        }
        engine.import_memories(payload)
        ids = engine.backend.find_by_terms({"imported"}, None)
        self.assertTrue(ids)
        results = engine.recall("imported 独特词", top_k=3)
        self.assertEqual(results[0].item.content, "imported 独特词")

    def test_import_episodic_updates_event_chain(self):
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        payload = {
            "memories": [
                {
                    "content": "alice bought camera on 2026-03-01.",
                    "kind": "episodic",
                    "source": user.to_dict(),
                    "cues": ["alice", "2026-03-01"],
                },
                {
                    "content": "alice visited kyoto on 2026-03-02.",
                    "kind": "episodic",
                    "source": user.to_dict(),
                    "cues": ["alice", "2026-03-02"],
                },
            ]
        }
        engine.import_memories(payload)
        items = engine.backend.list()
        first = next(item for item in items if "camera" in item.content)
        second = next(item for item in items if "kyoto" in item.content)
        self.assertEqual(engine.event_chain.next_event_id(first.id), second.id)

    def test_remember_many_links_are_deduplicated(self):
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        records = [
            {
                "content": f"项目 {index} 讨论会",
                "kind": MemoryKind.EPISODIC,
                "source": source,
                "cues": ["共同线索"],
            }
            for index in range(10)
        ]
        engine.remember_many(records)
        links = engine.backend.all_links()
        self.assertEqual(len(links), 90)  # 10 * 9 directed edges, no dups
        self.assertEqual(len({(a, b) for a, b, _ in links}), 90)

    def test_remember_many_dedupes_semantic_duplicates_in_batch(self):
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember_many(
            [
                {
                    "content": "重复事实 A",
                    "kind": MemoryKind.SEMANTIC,
                    "source": source,
                },
                {
                    "content": "重复事实 A",
                    "kind": MemoryKind.SEMANTIC,
                    "source": source,
                },
                {
                    "content": "重复事实 B",
                    "kind": MemoryKind.SEMANTIC,
                    "source": source,
                },
                {
                    "content": "独立事件 C",
                    "kind": MemoryKind.EPISODIC,
                    "source": source,
                },
            ]
        )
        stats = engine.stats()
        self.assertEqual(stats["semantic"], 2)
        self.assertEqual(stats["episodic"], 1)

    def test_zero_hit_recall_surfaces_old_high_importance_fact(self):
        """Core facts must survive the recency fallback (dual pool)."""
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        core = engine.remember(
            "我对花生严重过敏。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            importance=1.0,
            created_at=utcnow() - timedelta(days=365),
            auto_cues=False,
        )
        for index in range(20):
            engine.remember(
                f"最近普通记录 {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.3,
                auto_cues=False,
            )
        results = engine.recall("完全不相关的查询词", top_k=5)
        self.assertIn(core.id, {result.item.id for result in results})

    def test_remember_many_embeds_in_one_batch_call(self):
        embedder = _BatchCountingEmbedder()
        engine = MemoryEngine(
            vector_index=VectorIndex(dim=3),
            index_embedder=embedder,
        )
        try:
            source = SourceRecord(origin=SourceType.USER)
            records = [
                {
                    "content": f"批量向量记忆 {index}",
                    "kind": MemoryKind.EPISODIC,
                    "source": source,
                }
                for index in range(30)
            ]
            engine.remember_many(records)
            self.assertEqual(embedder.calls, 1)
            self.assertEqual(len(embedder.batches[0]), 30)
            self.assertEqual(engine.vector_index.size, 30)
        finally:
            engine.close()

    def test_remember_many_embed_failure_leaves_store_untouched(self):
        class _FailingEmbedder(Embedder):
            def embed(self, text: str) -> list[float]:
                return [1.0, 0.0, 0.0]

            def embed_many(self, texts: list[str]) -> list[list[float]]:
                raise EmbeddingAPIError("batch embedding failed")

        engine = MemoryEngine(
            vector_index=VectorIndex(dim=3),
            index_embedder=_FailingEmbedder(),
        )
        try:
            source = SourceRecord(origin=SourceType.USER)
            records = [
                {
                    "content": f"失败安全 {index}",
                    "kind": MemoryKind.EPISODIC,
                    "source": source,
                }
                for index in range(3)
            ]
            with self.assertRaises(EmbeddingAPIError):
                engine.remember_many(records)
            self.assertEqual(engine.backend.count(), 0)
        finally:
            engine.close()

    def test_rebuild_missing_vectors_repairs_failed_embed(self):
        class _FlakyEmbedder(Embedder):
            def __init__(self) -> None:
                self.fail = True

            def embed(self, text: str) -> list[float]:
                if self.fail:
                    raise EmbeddingAPIError("first attempt failed")
                return [1.0, 0.0, 0.0]

            def embed_many(self, texts: list[str]) -> list[list[float]]:
                if self.fail:
                    raise EmbeddingAPIError("first attempt failed")
                return [[1.0, 0.0, 0.0] for _ in texts]

        flaky = _FlakyEmbedder()
        engine = MemoryEngine(
            vector_index=VectorIndex(dim=3),
            index_embedder=flaky,
        )
        try:
            with self.assertRaises(EmbeddingAPIError):
                engine.remember(
                    "孤儿向量记忆",
                    kind=MemoryKind.EPISODIC,
                    source=SourceRecord(origin=SourceType.USER),
                )
            self.assertEqual(engine.backend.count(), 1)
            self.assertEqual(engine.vector_index.size, 0)
            flaky.fail = False
            rebuilt = engine.rebuild_missing_vectors()
            self.assertEqual(rebuilt, 1)
            self.assertEqual(engine.vector_index.size, 1)
        finally:
            engine.close()

    def test_idf_rare_term_survives_candidate_pruning(self):
        """A candidate matching one rare term must beat generic crowders."""
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        for index in range(120):
            engine.remember(
                f"common record {index}",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[],
                auto_cues=False,
            )
        rare = engine.remember(
            "Xyzzzy special event",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[],
            auto_cues=False,
        )
        results = engine.recall("common Xyzzzy", top_k=5)
        self.assertIn(rare.id, {result.item.id for result in results})

    def test_english_synonym_expansion_retrieves_cost_turns(self):
        """'money spent on expenses' must match turns written as 'cost'."""
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        cost_turn = engine.remember(
            "I remember taking my bike for a tune-up; it cost me $25.",
            kind=MemoryKind.EPISODIC,
            source=source,
        )
        engine.remember(
            "I've been tracking my bike mileage since the start of the year.",
            kind=MemoryKind.EPISODIC,
            source=source,
        )
        results = engine.recall(
            "How much money have I spent on bike expenses?", top_k=3
        )
        self.assertEqual(results[0].item.content, cost_turn.content)

    def test_dense_rerank_does_not_pad_to_budget(self):
        """Few lexical hits must not trigger 64 irrelevant embeddings."""
        counting = _BatchCountingEmbedder()
        engine = MemoryEngine(embedder=counting)
        try:
            source = SourceRecord(origin=SourceType.USER)
            for index in range(5):
                engine.remember(
                    f"alpha item {index}",
                    kind=MemoryKind.EPISODIC,
                    source=source,
                )
            for index in range(100):
                engine.remember(
                    f"other item {index}",
                    kind=MemoryKind.EPISODIC,
                    source=source,
                )
            engine.recall("alpha", top_k=3)
            # 5 lexical hits + 16 zero-overlap rescue budget, not 64.
            self.assertLessEqual(counting.calls, 21)
        finally:
            engine.close()

    def test_remember_many_builds_event_chain_in_order(self):
        """Batch ingestion must keep input order for the event chain."""
        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        engine.remember_many(
            [
                {
                    "content": "alice bought camera on 2026-03-01.",
                    "kind": MemoryKind.EPISODIC,
                    "source": source,
                    "cues": ["alice", "2026-03-01"],
                },
                {
                    "content": "alice visited kyoto on 2026-03-02.",
                    "kind": MemoryKind.EPISODIC,
                    "source": source,
                    "cues": ["alice", "2026-03-02"],
                },
            ]
        )
        items = engine.backend.list()
        first = next(item for item in items if "camera" in item.content)
        second = next(item for item in items if "kyoto" in item.content)
        self.assertEqual(engine.event_chain.next_event_id(first.id), second.id)


if __name__ == "__main__":
    unittest.main()
