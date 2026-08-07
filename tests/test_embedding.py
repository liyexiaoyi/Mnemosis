import unittest

from mnemosis import MemoryEngine
from mnemosis.embedding import Embedder, NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType


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


if __name__ == "__main__":
    unittest.main()
