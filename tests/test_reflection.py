import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class ReflectionTest(unittest.TestCase):
    def setUp(self):
        self.engine = MemoryEngine()
        self.user = SourceRecord(origin=SourceType.USER)

    def test_reflect_summarizes_supporting_episodes(self):
        self.engine.remember(
            "Episode alpha.",
            kind=MemoryKind.EPISODIC,
            source=self.user,
            cues=["topic"],
        )
        self.engine.remember(
            "Episode beta.",
            kind=MemoryKind.EPISODIC,
            source=self.user,
            cues=["topic"],
        )
        self.engine.remember(
            "draft summary",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
            cues=["topic"],
            evidence_count=2,
        )
        reflected = self.engine.reflect(
            summarizer=lambda contents: " | ".join(contents)
        )
        self.assertEqual(len(reflected), 1)
        self.assertEqual(reflected[0].content, "Episode alpha. | Episode beta.")
        refreshed = self.engine.backend.get(reflected[0].id)
        self.assertEqual(refreshed.content, "Episode alpha. | Episode beta.")

    def test_reflect_without_summarizer_is_noop(self):
        self.engine.remember(
            "draft summary",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
            cues=["topic"],
            evidence_count=2,
        )
        self.assertEqual(self.engine.reflect(), [])

    def test_sleep_with_summarizer_reflects(self):
        self.engine.remember(
            "Episode one.",
            kind=MemoryKind.EPISODIC,
            source=self.user,
            cues=["topic"],
        )
        self.engine.remember(
            "Episode two.",
            kind=MemoryKind.EPISODIC,
            source=self.user,
            cues=["topic"],
        )
        self.engine.remember(
            "placeholder summary",
            kind=MemoryKind.SEMANTIC,
            source=self.user,
            cues=["topic"],
            evidence_count=2,
        )
        report = self.engine.sleep(summarizer=lambda contents: "ABSTRACT")
        self.assertEqual(len(report.reflected), 1)
        self.assertEqual(report.reflected[0].content, "ABSTRACT")


if __name__ == "__main__":
    unittest.main()

