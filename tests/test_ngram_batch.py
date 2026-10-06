"""Batch-local feature reuse must preserve legacy vectors and custom dispatch."""
import hashlib
import importlib.util
from pathlib import Path
import random
import unittest
from unittest.mock import patch

from mnemosis.embedding import NGramEmbedder

_spec = importlib.util.spec_from_file_location(
    "frozen_ngram", Path(__file__).parent / "fixtures" / "ngram_4068385.py"
)
_old = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_old)


class NGramBatchTest(unittest.TestCase):
    def test_batch_reuses_feature_hashes_without_changing_vectors(self):
        texts = ["coffee tea 中文", "tea coffee 中文 coffee", "coffee 中文 tea"]
        engine = NGramEmbedder()
        expected = _old.NGramEmbedder().embed_many(texts)
        distinct = len(set(feature for text in texts for feature in engine.features(text)))
        with patch("mnemosis.embedding.hashlib.blake2b", wraps=hashlib.blake2b) as digest:
            actual = engine.embed_many(texts)
        self.assertEqual(actual, expected)
        self.assertEqual(digest.call_count, distinct)

    def test_seeded_vectors_exactly_match_frozen_oracle(self):
        rng = random.Random(20261006)
        texts = ["", "a", "tea tea tea", "中文技术 English COFFEE café Straße",
                 "𠮷 emoji 🐈 東京", "iİIı éÉ\u0301", "0 1 12 0012", "aa " * 100,
                 "x" * 300, "\x00 中文\n123 abc"]
        alphabet = "abcXYZ0123-_/ 中文记忆caféİıé\u0301🐈"
        texts += ["".join(rng.choices(alphabet, k=rng.randrange(1, 180))) for _ in range(80)]
        for dim, lo, hi in ((1, 2, 4), (3, 1, 3), (32, 2, 4), (256, 2, 4),
                            (16, 0, 2), (17, 3, 1), (33, 2, 300)):
            with self.subTest(dim=dim, lo=lo, hi=hi):
                current = NGramEmbedder(dim, lo, hi)
                old = _old.NGramEmbedder(dim, lo, hi)
                self.assertEqual(current.embed_many(texts), old.embed_many(texts))
                self.assertEqual([current.embed(t) for t in texts], old.embed_many(texts))

    def test_batch_preserves_subclass_embed_override(self):
        class Custom(NGramEmbedder):
            def embed(self, text):
                return [float(len(text))]
        self.assertEqual(Custom().embed_many(["a", "abcd"]), [[1.0], [4.0]])

    def test_batch_preserves_instance_embed_override(self):
        engine = NGramEmbedder()
        engine.embed = lambda text: [float(len(text))]
        self.assertEqual(engine.embed_many(["a", "abcd"]), [[1.0], [4.0]])

    def test_batch_preserves_feature_override_and_current_dimension(self):
        class CustomFeatures(NGramEmbedder):
            def features(self, text):
                return [text, "constant", text]
        engine = CustomFeatures(5)
        texts = ["tea", "coffee", "tea"]
        expected = [engine.embed(text) for text in texts]
        self.assertEqual(engine.embed_many(texts), expected)
        engine.dimension = 7
        self.assertEqual(engine.embed_many(texts), [engine.embed(t) for t in texts])

    def test_iterators_empty_and_single_batches_keep_existing_semantics(self):
        engine = NGramEmbedder()
        texts = ["coffee", "中文"]
        self.assertEqual(engine.embed_many(iter(texts)), [engine.embed(t) for t in texts])
        self.assertEqual(engine.embed_many([]), [])
        self.assertEqual(engine.embed_many(["tea"]), [engine.embed("tea")])

    def test_batch_does_not_retain_feature_cache_on_embedder(self):
        engine = NGramEmbedder()
        before = dict(vars(engine))
        engine.embed_many(["private lexical feature", "private lexical feature 中文"])
        self.assertEqual(vars(engine), before)

    def test_batch_hash_cache_stays_bounded_and_is_fresh_for_next_batch(self):
        import mnemosis.embedding as module
        snapshots = []
        caches = []
        class Watching(NGramEmbedder):
            def _embed_cached(self, text, cache):
                if not caches or caches[-1] is not cache:
                    caches.append(cache)
                    self_outer.assertEqual(len(cache), 0)
                result = super()._embed_cached(text, cache)
                snapshots.append(len(cache))
                return result
        self_outer = self
        engine = Watching()
        texts = [f"feature{i} 中文" for i in range(20)]
        with patch.object(module, "_NGRAM_BATCH_CACHE_LIMIT", 32, create=True):
            self.assertEqual(engine.embed_many(texts), _old.NGramEmbedder().embed_many(texts))
            self.assertEqual(engine.embed_many(texts), _old.NGramEmbedder().embed_many(texts))
        self.assertEqual(len(caches), 2)
        self.assertLessEqual(max(snapshots), 32)

    def test_very_long_feature_is_not_retained_in_batch_hash_cache(self):
        caches = []
        class SingleFeature(NGramEmbedder):
            def features(self, text):
                return [text]
            def _embed_cached(self, text, cache):
                result = super()._embed_cached(text, cache)
                caches.append(dict(cache))
                return result
        engine = SingleFeature()
        text = "x" * 1000
        expected = [engine.embed(text), engine.embed(text)]
        self.assertEqual(engine.embed_many([text, text]), expected)
        self.assertEqual(caches, [{}, {}])

    def test_batch_preserves_class_level_embed_replacement(self):
        engine = NGramEmbedder()
        with patch.object(NGramEmbedder, "embed", lambda self, text: [float(len(text))]):
            self.assertEqual(engine.embed_many(["a", "abcd"]), [[1.0], [4.0]])
