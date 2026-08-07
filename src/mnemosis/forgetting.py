"""Ebbinghaus forgetting curve and spaced-repetition review scheduler.

Human principle #2: memories decay with time; access and spaced review
strengthen them.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .types import MemoryItem, utcnow


class ForgettingCurve:
    """Exponential strength decay with access-based reinforcement."""

    def __init__(self, decay_rate: float = 0.002) -> None:
        """
        Args:
            decay_rate: per-hour decay exponent. 0.002 -> a memory loses about
                half its retrievability in ~14 days without access.
        """
        self.decay_rate = decay_rate

    def hours_since_last_access(
        self, item: MemoryItem, now: datetime | None = None
    ) -> float:
        anchor = item.last_access_at or item.created_at
        now = now or utcnow()
        return max(0.0, (now - anchor).total_seconds() / 3600.0)

    def retrievability(self, item: MemoryItem, now: datetime | None = None) -> float:
        """Current retrievability in [0, 1] after exponential decay."""
        hours = self.hours_since_last_access(item, now)
        return item.strength * math.exp(-self.decay_rate * hours)

    def reinforce(
        self,
        item: MemoryItem,
        delta: float = 0.1,
        now: datetime | None = None,
    ) -> float:
        """Strengthen a memory after access and record the access."""
        item.strength = min(1.0, item.strength + delta)
        item.touch(now or utcnow())
        return item.strength

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

    def next_interval_hours(self, access_count: int) -> float:
        """interval = base * 2 ** min(access_count - 1, 8)."""
        if access_count < 1:
            return self.base_interval_hours
        return self.base_interval_hours * (2 ** min(access_count - 1, 8))

    def next_review_at(
        self, item: MemoryItem, now: datetime | None = None
    ) -> datetime:
        now = now or utcnow()
        return now + timedelta(hours=self.next_interval_hours(item.access_count))

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
    ) -> list[MemoryItem]:
        now = now or utcnow()
        due = [
            item
            for item in items
            if self.is_due(item, now, due_threshold=due_threshold)
        ]
        due.sort(key=lambda i: self.curve.retrievability(i, now))
        return due[:limit]


__all__ = ["ForgettingCurve", "ReviewScheduler"]

