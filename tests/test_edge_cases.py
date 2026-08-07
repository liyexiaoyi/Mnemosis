import unittest

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class EdgeCaseTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()
        self.user = SourceRecord(origin=SourceType.USER)

    def test_recall_on_empty_store(self):
        self.assertEqual(self.engine.recall("anything"), [])
        self.assertEqual(self.engine.recall("anything", embedder=NGramEmbedder()), [])

    def test_empty_query_does_not_crash(self):
        self.engine.remember("A memory.", kind=MemoryKind.SEMANTIC, source=self.user)
        results = self.engine.recall("")
        self.assertIsInstance(results, list)

    def test_very_long_content(self):
        content = "word " * 5000
        item = self.engine.remember(
            content, kind=MemoryKind.SEMANTIC, source=self.user
        )
        self.assertIsNotNone(item.id)
        results = self.engine.recall("word", top_k=1)
        self.assertTrue(results)

    def test_unicode_and_emoji(self):
        item = self.engine.remember(
            "记忆测试 🧠 with emoji 🚀",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        results = self.engine.recall("记忆测试")
        self.assertEqual(results[0].item.id, item.id)

    def test_missing_ids_are_safe(self):
        self.assertIsNone(self.engine.update("nope", content="x"))
        self.assertFalse(self.engine.forget("nope"))
        self.assertFalse(self.engine.restore("nope"))

    def test_empty_working_set(self):
        self.assertEqual(self.engine.working_set(), [])

    def test_cjk_only_content(self):
        item = self.engine.remember(
            "王芳的项目名是 Atlas。",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
        )
        results = self.engine.recall("王芳 项目")
        self.assertEqual(results[0].item.id, item.id)


if __name__ == "__main__":
    unittest.main()

