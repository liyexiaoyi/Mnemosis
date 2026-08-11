"""Ebbinghaus forgetting curve and spaced-repetition review scheduler.

Human principle #2: memories decay with time; access and spaced review
strengthen them.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .types import MemoryItem, utcnow

EMOTIONAL_DECAY_FACTOR = 0.6
"""Emotionally arousing memories decay slower (Cahill & McGaugh, 1998)."""

EMOTION_PROCESSED_STREAK = 3
"""After this many consecutive successful retrievals the emotional charge
fades and decay returns to normal (emotion regulation / extinction-like
processing; Gross, 2002)."""


class ForgettingCurve:
    """Exponential strength decay with access-based reinforcement."""

    def __init__(self, decay_rate: float = 0.002) -> None:
        """
        Args:
            decay_rate: per-hour decay exponent. 0.002 -> a memory loses about
                half its retrievability in ~14 days without access.
        """
        self.decay_rate = decay_rate

    def effective_decay_rate(self, item: MemoryItem) -> float:
        """Slower decay for emotionally salient memories.

        Emotion regulation (Gross, 2002): repeatedly retrieving and
        processing an emotional memory (3+ consecutive successes) reduces
        its persistent emotional charge, so the trace stops decaying at the
        slow "always hot" rate and returns to the normal forgetting curve.
        """
        if item.affect in ("positive", "negative", "arousing"):
            if item.review_streak >= EMOTION_PROCESSED_STREAK:
                return self.decay_rate
            return self.decay_rate * EMOTIONAL_DECAY_FACTOR
        return self.decay_rate

    def hours_since_last_access(
        self, item: MemoryItem, now: datetime | None = None
    ) -> float:
        anchor = item.last_access_at or item.created_at
        now = now or utcnow()
        return max(0.0, (now - anchor).total_seconds() / 3600.0)

    def retrievability(self, item: MemoryItem, now: datetime | None = None) -> float:
        """Current retrievability after exponential decay.

        Bjork & Bjork (1992): retrieval strength decays fast, but higher
        storage strength slows the loss of access.
        """
        hours = self.hours_since_last_access(item, now)
        return (
            item.strength
            * item.storage_strength
            * math.exp(-self.effective_decay_rate(item) * hours)
        )

    def reinforce(
        self,
        item: MemoryItem,
        delta: float = 0.1,
        now: datetime | None = None,
    ) -> float:
        """Strengthen a memory after access and record the access.

        Retrieval strength recovers fast; storage strength accrues slowly but
        durably (Bjork & Bjork, 1992).
        """
        item.strength = min(1.0, item.strength + delta)
        item.storage_strength = min(2.0, item.storage_strength + delta * 0.3)
        item.touch(now or utcnow())
        return item.strength

    def reinforce_review(
        self,
        item: MemoryItem,
        delta: float = 0.1,
        now: datetime | None = None,
        *,
        effort: float = 1.0,
    ) -> float:
        """Spacing-aware reinforcement for a *successful* retrieval.

        Two learning-science effects modulate the gain:

        - Spacing effect (Cepeda et al., 2006): a successful retrieval after
          a longer gap produces a larger durable gain, up to a saturating
          ceiling (gains stop growing past ~7 days).
        - Retrieval effort (Bjork & Kroll, 2015; Kornell & Vaughn, 2016):
          the harder the successful retrieval, the stronger the
          reinforcement (desirable difficulty), scaled by ``effort`` in
          [0, 1] (0 = effortless, 1 = maximum effort).
        """
        now = now or utcnow()
        spacing_hours = self.hours_since_last_access(item, now)
        spacing_gain = 1.0 + 0.45 * min(1.0, spacing_hours / 168.0)
        effort_gain = 1.0 + 0.5 * max(0.0, min(1.0, effort))
        return self.reinforce(item, delta * spacing_gain * effort_gain, now)

    def is_forgotten(
        self, item: MemoryItem, threshold: float = 0.2, now: datetime | None = None
    ) -> bool:
        return self.retrievability(item, now) < threshold


class ReviewScheduler:
    """Spaced-repetition: review intervals grow with successful accesses."""

    def __init__(
        self, curve: ForgettingCurve, base_interval_hours: float = 24.0
    ) -> None:
        self.curve = curve
        self.base_interval_hours = base_interval_hours

    def next_interval_hours(self, access_count: float) -> float:
        """interval = base * 2 ** min(access_count - 1, 8).

        Fractional streaks (e.g. 0.5 from confidence-aware review) produce a
        shorter-than-base interval so uncertain memories are practised
        sooner; a failed review (streak 0) also returns sooner than base.
        """
        if access_count < 1:
            return self.base_interval_hours * (2 ** max(-2.0, access_count - 1))
        return self.base_interval_hours * (2 ** min(access_count - 1, 8))

    def next_review_at(
        self, item: MemoryItem, now: datetime | None = None
    ) -> datetime:
        """Next review uses the adaptive streak, not raw access count.

        ``review_streak`` counts consecutive *successful* reviews, which is
        the variable spaced repetition actually optimizes (Smolen et al.,
        2016). Failures reset the streak, so a struggling memory gets short
        intervals again instead of an ever-growing one. The next review is
        anchored to the last actual review time, so overdue traces are
        detectable.
        """
        now = now or utcnow()
        anchor = item.last_review_at or now
        return anchor + timedelta(
            hours=self.next_interval_hours(item.review_streak)
        )

    def record_outcome(
        self, item: MemoryItem, success: bool, now: datetime | None = None
    ) -> None:
        """Update review scheduling state from a retrieval outcome.

        Adaptive spacing (Cepeda et al., 2006; Smolen et al., 2016): a
        successful retrieval at the scheduled review extends the streak (next
        interval grows); a failure resets the streak and keeps the next
        interval short so the trace is re-presented soon.
        """
        now = now or utcnow()
        item.review_streak = item.review_streak + 1 if success else 0
        if success:
            item.retrieval_successes += 1
        else:
            item.retrieval_failures += 1
        item.last_review_at = now

    def is_due(
        self,
        item: MemoryItem,
        now: datetime | None = None,
        due_threshold: float = 0.5,
    ) -> bool:
        """Due when retrievability has dropped below the threshold."""
        return self.curve.retrievability(item, now) < due_threshold

    def due_items(
        self,
        items: list[MemoryItem],
        now: datetime | None = None,
        limit: int = 10,
        due_threshold: float = 0.5,
        importance_first: bool = True,
        desirable_difficulty: bool = False,
        difficulty_target: float = 0.45,
    ) -> list[MemoryItem]:
        """Due memories, most important first.

        Rasch & Born (2013): consolidation and rehearsal prioritise salient
        content. When the daily review quota is limited, high-importance due
        memories are selected before low-importance ones (ties broken by
        retrievability, most forgotten first).

        Desirable difficulty (Bjork & Bjork, 2011; Bjork, 1994): within an
        importance group, prefer due memories whose retrievability is
        closest to ``difficulty_target`` - hard enough to require effort
        (which strengthens more) but easy enough to succeed. This replaces
        "most forgotten first", which tends to schedule failures.
        """
        now = now or utcnow()
        due = [
            item
            for item in items
            if self.is_due(item, now, due_threshold=due_threshold)
        ]
        if desirable_difficulty:
            def _dd_key(item: MemoryItem) -> tuple:
                retrievability = self.curve.retrievability(item, now)
                difficulty = abs(retrievability - difficulty_target)
                if importance_first:
                    return (-item.importance, difficulty)
                return (difficulty,)

            due.sort(key=_dd_key)
            return due[:limit]
        if importance_first:
            due.sort(
                key=lambda i: (
                    -i.importance,
                    self.curve.retrievability(i, now),
                )
            )
        else:
            due.sort(key=lambda i: self.curve.retrievability(i, now))
        return due[:limit]


__all__ = ["ForgettingCurve", "ReviewScheduler"]
