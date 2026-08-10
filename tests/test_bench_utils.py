"""Tests for benchmark helper utilities (segment_text / keyword_correct)."""

from __future__ import annotations

import os
import sys

_BENCH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "benchmarks")
)
sys.path.insert(0, _BENCH)

from longmemeval_bench import keyword_correct, segment_text  # noqa: E402


def test_segment_text_keeps_abbreviations_together() -> None:
    text = (
        "Dr. Smith recommended the plan. We agreed with Mr. Jones on Tuesday. "
        "The U.S. market is growing fast."
    )
    segments = segment_text(text, min_len=10, max_segments=10)
    assert any("Dr. Smith" in part for part in segments)
    assert any("Mr. Jones" in part for part in segments)
    assert any("U.S. market" in part for part in segments)


def test_segment_text_splits_sentences() -> None:
    text = "First sentence here. Second sentence there. Third one."
    segments = segment_text(text, min_len=5, max_segments=10)
    assert len(segments) == 3


def test_keyword_correct_is_token_based() -> None:
    assert keyword_correct("q", "cat", "I have a cat.")
    assert not keyword_correct("q", "cat", "I saw a category.")
    assert not keyword_correct("q", "cat", "unknown")
