import numbers
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

    def test_zero_hit_semantic_fallback_reranks_whole_pool(self):
        """With an embedder, a relevant memory ranked beyond 64 still wins."""

        class _FakeSemanticEmbedder(Embedder):
            def embed(self, text: str) -> list[float]:
                if "coffee" in text or "beverage" in text:
                    return [1.0, 0.0]
                return [0.0, 1.0]

        engine = MemoryEngine(embedder=_FakeSemanticEmbedder())
        source = SourceRecord(origin=SourceType.USER)
        relevant = engine.remember(
            "coffee morning routine",
            kind=MemoryKind.SEMANTIC,
            source=source,
            importance=0.3,
            auto_cues=False,
        )
        for index in range(200):
            engine.remember(
                f"meeting minutes {index} purchase invoice approval",
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.3,
                auto_cues=False,
            )
        results = engine.recall("beverage habit", top_k=5)
        self.assertIn(relevant.id, {result.item.id for result in results})

    def test_zero_hit_remote_embedder_rerank_pool_is_capped(self):
        """Network embedders must not embed the whole fallback pool."""

        class _RemoteEmbedder(Embedder):
            remote = True

            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0, 0.0, 0.0]

        remote = _RemoteEmbedder()
        engine = MemoryEngine(embedder=remote)
        source = SourceRecord(origin=SourceType.USER)
        for index in range(100):
            engine.remember(
                f"unrelated record {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                auto_cues=False,
            )
        engine.recall("zzzz no hits", top_k=5)
        self.assertLessEqual(remote.calls, 65)  # query + capped re-rank pool

    def test_rerank_pool_params_are_configurable(self):
        class _CountingEmbedder(Embedder):
            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0, 0.0, 0.0]

        counting = _CountingEmbedder()
        engine = MemoryEngine(
            embedder=counting,
            dense_rerank_candidates=4,
            zero_hit_rerank_pool=10,
        )
        source = SourceRecord(origin=SourceType.USER)
        for index in range(30):
            engine.remember(
                f"alpha record {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                auto_cues=False,
            )
        engine.recall("alpha", top_k=3)
        self.assertLessEqual(counting.calls, 5)  # query + 4-candidate pool
        counting.calls = 0
        engine.recall("zzzz", top_k=3)
        self.assertLessEqual(counting.calls, 11)  # query + 10-candidate pool

    def test_rerank_pool_early_terminates_on_score_cliff(self):
        """Remote embedders stop embedding once lexical scores drop sharply."""

        class _RemoteEmbedder(Embedder):
            remote = True

            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0, 0.0, 0.0]

        remote = _RemoteEmbedder()
        engine = MemoryEngine(
            embedder=remote,
            dense_rerank_candidates=20,
            zero_hit_rerank_pool=20,
        )
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "alpha beta strong",
            kind=MemoryKind.EPISODIC,
            source=source,
            importance=1.0,
            auto_cues=False,
        )
        for index in range(15):
            engine.remember(
                "alpha " + "filler word " * 15 + f"weak {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.05,
                strength=0.1,
                auto_cues=False,
            )
        engine.recall("alpha beta", top_k=3)
        # query + the minimum re-rank pool (4), NOT all 16 candidates.
        self.assertLessEqual(remote.calls, 5)

    def test_rerank_min_pool_prevents_over_cut(self):
        """Even an extreme top score keeps at least 4 candidates embedded."""

        class _RemoteEmbedder(Embedder):
            remote = True

            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0, 0.0, 0.0]

        remote = _RemoteEmbedder()
        engine = MemoryEngine(
            embedder=remote,
            dense_rerank_candidates=20,
            zero_hit_rerank_pool=20,
        )
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "alpha beta gamma",
            kind=MemoryKind.EPISODIC,
            source=source,
            importance=1.0,
            auto_cues=False,
        )
        for index in range(15):
            engine.remember(
                "beta gamma " + "filler word " * 15 + f"paraphrase {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.05,
                strength=0.1,
                auto_cues=False,
            )
        engine.recall("alpha beta gamma", top_k=3)
        # top score is extreme; without the min-pool the tail would be cut
        # to 1 candidate, but the min pool keeps 4 (query + 4 calls).
        self.assertEqual(remote.calls, 5)

    def test_rerank_flat_score_distribution_is_not_cut(self):
        """Slowly decaying scores must not trigger the cliff cut."""

        class _RemoteEmbedder(Embedder):
            remote = True

            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0, 0.0, 0.0]

        remote = _RemoteEmbedder()
        engine = MemoryEngine(
            embedder=remote,
            dense_rerank_candidates=20,
            zero_hit_rerank_pool=20,
        )
        source = SourceRecord(origin=SourceType.USER)
        for index in range(16):
            engine.remember(
                f"alpha beta shared content {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.5,
                auto_cues=False,
            )
        engine.recall("alpha beta", top_k=3)
        # Scores are nearly identical (no cliff), so all 16 are embedded.
        self.assertEqual(remote.calls, 17)

    def test_rerank_low_score_region_is_not_over_cut(self):
        """A small absolute gap in a low-score region is not a cliff."""

        class _RemoteEmbedder(Embedder):
            remote = True

            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0, 0.0, 0.0]

        remote = _RemoteEmbedder()
        engine = MemoryEngine(
            embedder=remote,
            dense_rerank_candidates=20,
            zero_hit_rerank_pool=20,
        )
        source = SourceRecord(origin=SourceType.USER)
        for index in range(16):
            engine.remember(
                f"alpha beta low score {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.01,
                strength=0.1,
                auto_cues=False,
            )
        engine.recall("alpha beta", top_k=3)
        # gap ~0.03 absolute but <30% relative -> no cliff, all embedded.
        self.assertEqual(remote.calls, 17)

    def test_rerank_uses_batch_embedding_for_remote(self):
        """A 16-candidate pool must produce one embed_many call."""

        class _BatchRemoteEmbedder(Embedder):
            remote = True

            def __init__(self) -> None:
                self.embed_calls = 0
                self.embed_many_calls = 0
                self.batch_sizes: list[int] = []

            def embed(self, text: str) -> list[float]:
                self.embed_calls += 1
                return [1.0, 0.0, 0.0]

            def embed_many(self, texts: list[str]) -> list[list[float]]:
                self.embed_many_calls += 1
                self.batch_sizes.append(len(texts))
                return [[1.0, 0.0, 0.0] for _ in texts]

        embedder = _BatchRemoteEmbedder()
        engine = MemoryEngine(
            embedder=embedder,
            dense_rerank_candidates=20,
            zero_hit_rerank_pool=20,
        )
        source = SourceRecord(origin=SourceType.USER)
        for index in range(16):
            engine.remember(
                f"alpha beta shared content {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                importance=0.5,
                auto_cues=False,
            )
        engine.recall("alpha beta", top_k=3)
        self.assertEqual(embedder.embed_many_calls, 1)
        self.assertEqual(embedder.batch_sizes, [16])
        self.assertLessEqual(embedder.embed_calls, 16)  # query + cache misses

    def test_embed_cache_respects_lru_limit(self):
        class _CountingEmbedder(Embedder):
            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0, 0.0, 0.0]

        counting = _CountingEmbedder()
        engine = MemoryEngine(embedder=counting, embed_cache_limit=2)
        source = SourceRecord(origin=SourceType.USER)
        for index in range(4):
            engine.remember(
                f"topic {index} content",
                kind=MemoryKind.EPISODIC,
                source=source,
                auto_cues=False,
            )
        for index in range(4):
            engine.recall(f"topic {index}", top_k=1)
        self.assertLessEqual(len(engine.store._embed_cache), 2)
        before = counting.calls
        engine.recall("topic 0", top_k=1)
        # topic 0 was evicted (LRU) -> must be embedded again
        self.assertGreater(counting.calls, before)

    def test_embed_cache_respects_byte_limit(self):
        class _HighDimCountingEmbedder(Embedder):
            def __init__(self) -> None:
                self.calls = 0

            def embed(self, text: str) -> list[float]:
                self.calls += 1
                return [1.0] * 128  # 512 estimated bytes per vector

        counting = _HighDimCountingEmbedder()
        engine = MemoryEngine(
            embedder=counting,
            embed_cache_limit=1000,  # deliberately loose count bound
            # 128-dim list[float] estimates to 128*32+64 = 4160 bytes each;
            # 0.008 MB ≈ 8388 bytes fits exactly two vectors.
            embed_cache_memory_limit_mb=0.008,
        )
        source = SourceRecord(origin=SourceType.USER)
        for index in range(4):
            engine.remember(
                f"byte topic {index} content",
                kind=MemoryKind.EPISODIC,
                source=source,
                auto_cues=False,
            )
        for index in range(4):
            engine.recall(f"byte topic {index}", top_k=1)
        self.assertLessEqual(len(engine.store._embed_cache), 2)
        self.assertLessEqual(engine.store._embed_cache_bytes, 8389)
        before = counting.calls
        engine.recall("byte topic 0", top_k=1)
        # topic 0 was evicted by the byte budget -> must be embedded again
        self.assertGreater(counting.calls, before)

    def test_embed_cache_byte_accounting_deduplicates_shared_content(self):
        class _FixedDimEmbedder(Embedder):
            def embed(self, text: str) -> list[float]:
                return [0.25] * 64  # 64*32+64 = 2112 estimated bytes

        embedder = _FixedDimEmbedder()
        engine = MemoryEngine(
            embedder=embedder,
            embed_cache_limit=100,
            embed_cache_memory_limit_mb=None,
        )
        source = SourceRecord(origin=SourceType.USER)
        for _ in range(3):
            engine.remember(
                "identical shared text",
                kind=MemoryKind.EPISODIC,
                source=source,
                auto_cues=False,
            )
        engine.recall("identical shared text", top_k=3)
        self.assertEqual(engine.store._embed_cache_bytes, 2112)

    def test_embed_cache_byte_estimate_uses_nbytes_for_compact_arrays(self):
        class _NumpyLikeInt:
            """Simulates numpy.int64: not a subclass of builtin int."""

            def __init__(self, value: int) -> None:
                self.value = value

            def __int__(self) -> int:
                return self.value

            def __gt__(self, other) -> bool:
                return self.value > other

        numbers.Integral.register(_NumpyLikeInt)

        class _CompactVector:
            def __init__(self, size: int, nbytes_value=None) -> None:
                self._data = [0.0] * size
                self.nbytes = (
                    nbytes_value if nbytes_value is not None else size * 4
                )

            def __len__(self) -> int:
                return len(self._data)

            def __iter__(self):
                return iter(self._data)

        class _ArrayEmbedder(Embedder):
            def embed(self, text: str) -> _CompactVector:
                return _CompactVector(128)

        engine = MemoryEngine(
            embedder=_ArrayEmbedder(),
            embed_cache_limit=100,
            embed_cache_memory_limit_mb=None,
        )
        source = SourceRecord(origin=SourceType.USER)
        engine.remember(
            "compact array vector",
            kind=MemoryKind.EPISODIC,
            source=source,
            auto_cues=False,
        )
        engine.recall("compact array vector", top_k=1)
        # Compact arrays are measured by nbytes (128*4), not len*32.
        self.assertEqual(engine.store._embed_cache_bytes, 512)

        numpy_like = MemoryEngine(
            embedder=_ArrayEmbedder(),
            embed_cache_limit=100,
            embed_cache_memory_limit_mb=None,
        )
        numpy_like.store._embed_cache_bytes = 0
        numpy_like.store._embed_cache.clear()
        vector = _CompactVector(128, _NumpyLikeInt(1024))
        numpy_like.store._embed_cache["k"] = vector  # type: ignore[index]
        numpy_like.store._embed_cache_bytes += (
            numpy_like.store._vector_cache_bytes(vector)
        )
        # numpy-like ints (not builtin int) must still be recognized.
        self.assertEqual(numpy_like.store._embed_cache_bytes, 1024)

    def test_embed_cache_byte_limit_smaller_than_one_vector(self):
        class _BigVectorEmbedder(Embedder):
            def embed(self, text: str) -> list[float]:
                return [1.0] * 128  # 4160 estimated bytes per vector

        engine = MemoryEngine(
            embedder=_BigVectorEmbedder(),
            embed_cache_limit=100,
            embed_cache_memory_limit_mb=0.00005,  # ~52 bytes < one vector
        )
        source = SourceRecord(origin=SourceType.USER)
        for index in range(3):
            engine.remember(
                f"tiny budget topic {index}",
                kind=MemoryKind.EPISODIC,
                source=source,
                auto_cues=False,
            )
        for index in range(3):
            engine.recall(f"tiny budget topic {index}", top_k=1)
        # Every vector exceeds the byte budget, so each insert is evicted
        # immediately; the cache must stay empty without looping forever.
        self.assertEqual(len(engine.store._embed_cache), 0)
        self.assertEqual(engine.store._embed_cache_bytes, 0)

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
