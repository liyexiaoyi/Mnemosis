"""Conservative event time resolution for the opt-in source policy.

Occurrence is not factual validity. Import/update/access clocks never enter
this resolver. Unknown or conflicting dates remain unknown.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timezone, tzinfo
import re

from .types import MemoryItem, MemoryKind

_FULL = re.compile(r"(?<!\d)(?:(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日|(\d{4})-(\d{1,2})-(\d{1,2}))(?!\d)")
_MD = re.compile(r"(\d{1,2})\s*月\s*(\d{1,2})\s*日")
_REFERENCE = re.compile(r"生日|出生日期|引用|举例|示例")

@dataclass(frozen=True)
class EventTime:
    day: date | None
    instant: datetime | None = None
    basis: str = "unknown"
    issue: str | None = None

    def order_key(self, zone: tzinfo) -> datetime:
        if self.day is None:
            raise ValueError("unknown event time has no chronological key")
        return (self.instant or datetime.combine(self.day, time.min, zone)).astimezone(timezone.utc)


def resolve_event_time(item: MemoryItem, *, zone: tzinfo = timezone.utc) -> EventTime:
    """Resolve one numeric Chinese/ISO event date, or aware episodic source.

    A source timestamp supplies sub-day precision only for an episode.
    A date-only body keeps day precision. Multiple dates, invalid dates,
    reference dates and disagreements are deliberately not disambiguated.
    """
    full: set[date] = set()
    partial: set[tuple[int, int]] = set()
    for text in (item.content, " ".join(item.cues)):
        matches = list(_FULL.finditer(text))
        if (matches or _MD.search(text)) and _REFERENCE.search(text):
            return EventTime(None, issue="正文日期可能是引用或个人属性")
        for match in matches:
            values = match.groups()[:3] if match.group(1) else match.groups()[3:]
            try:
                full.add(date(*(int(x) for x in values)))
            except ValueError:
                return EventTime(None, issue="正文日期无效")
        for match in _MD.finditer(text):
            if any(start.start() <= match.start() < start.end() for start in matches):
                continue
            matched_md = (int(match.group(1)), int(match.group(2)))
            try:
                date(2000, *matched_md)
            except ValueError:
                return EventTime(None, issue="正文月日无效")
            partial.add(matched_md)
    if len(full) > 1 or len(partial) > 1:
        return EventTime(None, issue="多日期无法归属单一事件")
    instant = None
    if item.kind is MemoryKind.EPISODIC and item.source.occurred_at is not None:
        stamp = item.source.occurred_at
        if stamp.tzinfo is None or stamp.utcoffset() is None:
            return EventTime(None, issue="来源发生时间缺少时区")
        try:
            instant = stamp.astimezone(zone)
        except (ValueError, OverflowError):
            return EventTime(None, issue="来源时间无法换算")
    body = next(iter(full), None)
    md = next(iter(partial), None)
    if body is not None and md is not None and (body.month, body.day) != md:
        return EventTime(None, issue="多日期无法归属单一事件")
    if body is not None:
        if instant is not None and body != instant.date():
            return EventTime(None, issue="正文与来源发生时间冲突")
        return EventTime(body, instant, "正文事件日期+来源发生时间" if instant else "正文事件日期")
    if md is not None and (instant is None or (instant.month, instant.day) != md):
        return EventTime(None, issue="无年份日期缺少一致的来源依据")
    if instant is not None:
        return EventTime(instant.date(), instant, "来源发生时间")
    return EventTime(None, issue="缺少可用事件时间")


__all__ = ["EventTime", "resolve_event_time"]
