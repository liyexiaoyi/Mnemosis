"""Importance scoring.

Human principle #3: humans prioritize what matters to them. Mnemosis scores
importance from explicit signals, affect words, frequency and source trust.
An optional LLM scorer can replace the rules.
"""

from __future__ import annotations

from typing import Callable

from .types import SourceRecord


STRONG_WORDS = {
    "重要", "记住", "务必", "必须", "永远", "关键", "核心", "最重要",
    "important", "remember", "critical", "essential", "always", "never",
    "priority", "must",
}

AFFECT_WORDS = {
    "喜欢", "讨厌", "害怕", "开心", "难过", "焦虑", "感动", "生气",
    "love", "hate", "afraid", "happy", "sad", "anxious", "angry",
}


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


class ImportanceScorer:
    """Rule-based importance scorer with an optional LLM hook."""

    def __init__(
        self,
        llm_scorer: Callable[[str, dict], float] | None = None,
    ) -> None:
        self.llm_scorer = llm_scorer

    def score(
        self,
        content: str,
        *,
        source: SourceRecord | None = None,
        access_count: int = 0,
        explicit: float | None = None,
    ) -> float:
        """Score importance in [0, 1]."""
        if explicit is not None:
            return clamp01(explicit)
        if self.llm_scorer is not None:
            try:
                return clamp01(float(self.llm_scorer(content, {"source": source})))
            except (TypeError, ValueError):
                pass  # fall back to rules

        lowered = content.lower()
        score = 0.4
        score += 0.25 * (sum(w in lowered for w in STRONG_WORDS) > 0)
        score += 0.15 * (sum(w in lowered for w in AFFECT_WORDS) > 0)
        if source is not None:
            score += 0.1 * source.trust
        score += 0.1 * min(access_count / 5.0, 1.0)
        return clamp01(score)


__all__ = ["ImportanceScorer"]

