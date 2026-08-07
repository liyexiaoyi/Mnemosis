import unittest
from datetime import timedelta

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


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


if __name__ == "__main__":
    unittest.main()
