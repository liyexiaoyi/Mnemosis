"""Tests for benchmark helper utilities (segment_text / keyword_correct)."""

from __future__ import annotations

import os
import sys
import unittest

_BENCH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "benchmarks")
)
sys.path.insert(0, _BENCH)

from longmemeval_bench import keyword_correct, segment_text


class BenchUtilsTests(unittest.TestCase):
    def test_segment_text_keeps_abbreviations_together(self) -> None:
        text = (
            "Dr. Smith recommended the plan. We agreed with Mr. Jones on "
            "Tuesday. The U.S. market is growing fast."
        )
        segments = segment_text(text, min_len=10, max_segments=10)
        self.assertTrue(any("Dr. Smith" in part for part in segments))
        self.assertTrue(any("Mr. Jones" in part for part in segments))
        self.assertTrue(any("U.S. market" in part for part in segments))

    def test_segment_text_splits_sentences(self) -> None:
        text = "First sentence here. Second sentence there. Third one."
        segments = segment_text(text, min_len=5, max_segments=10)
        self.assertEqual(len(segments), 3)

    def test_keyword_correct_is_token_based(self) -> None:
        self.assertTrue(keyword_correct("q", "cat", "I have a cat."))
        self.assertFalse(keyword_correct("q", "cat", "I saw a category."))
        self.assertFalse(keyword_correct("q", "cat", "unknown"))


if __name__ == "__main__":
    unittest.main()
