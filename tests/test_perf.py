"""Coarse performance regression guards (generous bounds for CI variance)."""

import time
import unittest

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


class PerfRegressionTest(unittest.TestCase):
    def test_recall_and_sleep_scale_with_many_memories(self):
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        count = 1000

        start = time.perf_counter()
        for i in range(count):
            engine.remember(
                f"User {i} prefers topic-{i} for discussions.",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[f"topic-{i}"],
                importance=0.5,
                auto_cues=False,
            )
        encode_seconds = time.perf_counter() - start

        start = time.perf_counter()
        results = engine.recall("topic-777", top_k=5)
        recall_seconds = time.perf_counter() - start

        start = time.perf_counter()
        engine.sleep()
        sleep_seconds = time.perf_counter() - start

        self.assertTrue(results)
        self.assertIn("topic-777", results[0].item.content)
        self.assertLess(encode_seconds, 10.0)
        self.assertLess(recall_seconds, 3.0)
        self.assertLess(sleep_seconds, 3.0)


if __name__ == "__main__":
    unittest.main()

