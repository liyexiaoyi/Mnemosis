import unittest
import urllib.error
from unittest import mock

from mnemosis import MemoryEngine
from mnemosis.embedding import (
    CallableEmbedder,
    Embedder,
    EmbeddingAPIError,
    NGramEmbedder,
    _chunk_texts,
    make_embedder,
)
from mnemosis.types import MemoryKind, SourceRecord, SourceType
from mnemosis.vector_index import VectorIndex


class NGramEmbedderTest(unittest.TestCase):
    def setUp(self):
        self.embedder = NGramEmbedder()

    def test_cosine_prefers_synonyms_over_unrelated(self):
        color_colour = self.embedder.cosine(
            self.embedder.embed("color"), self.embedder.embed("colour")
        )
        color_paris = self.embedder.cosine(
            self.embedder.embed("color"), self.embedder.embed("paris")
        )
        self.assertGreater(color_colour, color_paris)
        self.assertGreater(color_colour, 0.3)

    def test_embedding_is_deterministic(self):
        first = self.embedder.embed("The quick brown fox.")
        second = self.embedder.embed("The quick brown fox.")
        self.assertEqual(first, second)

    def test_cjk_similarity(self):
        zh_tech = self.embedder.cosine(
            self.embedder.embed("中文"), self.embedder.embed("中文技术")
        )
        zh_en = self.embedder.cosine(
            self.embedder.embed("中文"), self.embedder.embed("英文")
        )
        self.assertGreater(zh_tech, zh_en)

    def test_unit_norm_cosine_matches_base(self):
        first = self.embedder.embed("color")
        second = self.embedder.embed("colour")
        self.assertAlmostEqual(
            self.embedder.cosine(first, second),
            Embedder.cosine(first, second),
            places=6,
        )


class EmbedderRecallTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine(embedder=NGramEmbedder())
        self.user = SourceRecord(origin=SourceType.USER)

    def test_recall_ranks_semantic_match_first(self):
        color = self.engine.remember(
            "She likes the color blue.",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        self.engine.remember(
            "She likes the city Paris.",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        results = self.engine.recall("what colour does she like?", top_k=2)
        self.assertEqual(results[0].item.id, color.id)
        self.assertGreater(results[0].score, results[1].score)

    def test_default_engine_is_unchanged(self):
        plain = MemoryEngine()
        plain.remember(
            "She likes the color blue.",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        self.assertTrue(plain.recall("color blue", top_k=1))

    def test_check_accepts_embedder(self):
        self.engine.remember(
            "She likes the color blue.",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        check = self.engine.check("what colour does she like?")
        self.assertTrue(check.items)

    def test_knowledge_gaps_respect_embedder(self):
        self.engine.remember(
            "The user prefers Chinese.",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        check = self.engine.check("the user's preference")
        self.assertNotIn("preference", check.gaps)

        plain = MemoryEngine()
        plain.remember(
            "The user prefers Chinese.",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        self.assertIn("preference", plain.check("the user's preference").gaps)

    def test_per_call_embedder_override(self):
        plain = MemoryEngine()
        item = plain.remember(
            "She likes the color blue.",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        results = plain.recall(
            "what colour does she like?", top_k=1, embedder=NGramEmbedder()
        )
        self.assertEqual(results[0].item.id, item.id)

    def test_same_type_different_cache_key_does_not_share_cache(self):
        class _ModelEmbedder(Embedder):
            def __init__(self, key: str, seen: list[str]) -> None:
                self.cache_key = key
                self.seen = seen

            def embed(self, text: str) -> list[float]:
                self.seen.append(text)
                return [1.0, 0.0, 0.0]

        first_seen: list[str] = []
        second_seen: list[str] = []
        engine = MemoryEngine()
        engine.remember(
            "bicycle content",
            kind=MemoryKind.EPISODIC,
            source=self.user,
            auto_cues=False,
        )
        engine.recall(
            "bicycle", top_k=1, embedder=_ModelEmbedder("model-a", first_seen)
        )
        engine.recall(
            "bicycle", top_k=1, embedder=_ModelEmbedder("model-b", second_seen)
        )
        self.assertTrue(first_seen)
        self.assertTrue(second_seen)  # different model -> no cache sharing


class EmbedderFactoryTest(unittest.TestCase):
    def test_none_disables_dense(self):
        self.assertIsNone(make_embedder(None))
        self.assertIsNone(make_embedder("none"))

    def test_unknown_provider_raises(self):
        with self.assertRaises(ValueError):
            make_embedder("bogus")

    def test_ollama_builds_without_network(self):
        self.assertIsInstance(make_embedder("ollama"), CallableEmbedder)

    def test_openai_requires_key(self):
        with self.assertRaises(ValueError):
            make_embedder("openai", api_key="")

    def test_openai_cache_key_normalizes_base_url(self):
        with_slash = make_embedder(
            "openai", api_key="k", base_url="https://api.test/v1/"
        )
        without_slash = make_embedder(
            "openai", api_key="k", base_url="https://api.test/v1"
        )
        self.assertEqual(with_slash.cache_key, without_slash.cache_key)

    def test_dense_recall_wiring(self):
        def fake(text: str) -> list[float]:
            return [1.0 if "猫" in text else 0.0, 1.0]

        embedder = CallableEmbedder(fake)
        engine = MemoryEngine(
            embedder=embedder,
            index_embedder=embedder,
            vector_index=VectorIndex(":memory:"),
        )
        engine.remember("用户喜欢猫", auto_cues=False)
        results = engine.recall_fused(
            "猫",
            dense_embedder=embedder,
            vector_index=engine.vector_index,
            top_k=1,
        )
        self.assertTrue(results)
        self.assertTrue(
            any("semantic" in reason for reason in results[0].reasons)
        )
        engine.vector_index.close()
        engine.close()

    def test_http_error_becomes_embedding_api_error(self):
        import io

        def fake_urlopen(req, timeout=None):
            raise urllib.error.HTTPError(
                req.full_url, 401, "Unauthorized", {},
                io.BytesIO(b'{"error":"bad api key"}'),
            )

        embedder = make_embedder("openai", api_key="test")
        with (
            mock.patch("urllib.request.urlopen", side_effect=fake_urlopen),
            self.assertRaises(EmbeddingAPIError) as ctx,
        ):
            embedder.embed("hello")
        self.assertIn("401", str(ctx.exception))

    def test_post_json_retries_429_then_succeeds(self):
        import io
        import json

        from mnemosis.embedding import _post_json

        attempts = {"count": 0}

        class _FakeResponse:
            def __init__(self, payload: bytes) -> None:
                self._payload = payload

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self._payload

        def fake_urlopen(req, timeout=None):
            attempts["count"] += 1
            if attempts["count"] < 3:
                raise urllib.error.HTTPError(
                    req.full_url, 429, "Too Many", {},
                    io.BytesIO(b'{"error":"slow down"}'),
                )
            return _FakeResponse(
                json.dumps({"ok": True}).encode("utf-8")
            )

        with mock.patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = _post_json(
                "http://example.test/v1", {}, {"Content-Type": "application/json"},
                timeout=5,
            )
        self.assertEqual(result, {"ok": True})
        self.assertEqual(attempts["count"], 3)

    def test_chunk_texts_respects_size_limits(self):
        texts = ["x" * 3000, "y" * 3000, "z" * 3000]
        chunks = _chunk_texts(texts, max_chars=6000, max_items=2)
        self.assertEqual([len(chunk) for chunk in chunks], [2, 1])

    def test_ollama_embed_many_checks_result_length(self):
        import io

        def fake_urlopen(req, timeout=None):
            return io.BytesIO(b'{"embeddings": [[0.1, 0.2]]}')

        from mnemosis.embedding import ollama_embedder

        embedder = ollama_embedder()
        with (
            mock.patch("urllib.request.urlopen", side_effect=fake_urlopen),
            self.assertRaises(EmbeddingAPIError),
        ):
            embedder.embed_many(["a", "b"])


if __name__ == "__main__":
    unittest.main()
