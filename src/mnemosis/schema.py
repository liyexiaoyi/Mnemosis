"""Event-chain (schema) memory: linking ordered episodes into a timeline.

Human principle (Gilboa & Marlatte, 2017; Bartlett, 1932): experiences are
stored not as isolated snapshots but as parts of *schematic sequences* —
event schemas ("what typically happens next"). Mnemosis keeps a lightweight
event-chain index: episodes sharing a person + session are ordered by date,
and each event knows its chronological successor. Recall can then follow the
chain, the same way "after X, what happened?" is answered from a script.
"""

from __future__ import annotations

import itertools
import re
from datetime import date, timezone, tzinfo

from .backend import Backend
from .event_time import resolve_event_time
from .types import MemoryItem, MemoryKind, MemoryStatus

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_SESSION_RE = re.compile(r"session(\d+)")


def _date_of(item: MemoryItem, *, date_policy: str = "content",
             event_timezone: tzinfo = timezone.utc) -> date | None:
    """Extract the event date from content or cues, if present."""
    if date_policy == "source":
        return resolve_event_time(item, zone=event_timezone).day
    if date_policy != "content":
        raise ValueError("date_policy must be content or source")
    for text in (item.content, " ".join(item.cues)):
        match = _DATE_RE.search(text)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                continue
    return None


def _person_and_session(item: MemoryItem) -> tuple[str, int | None]:
    """Infer (person, session) from cues like 'alice' + 'session3'."""
    person = ""
    session: int | None = None
    for cue in item.cues:
        if cue.startswith("session"):
            match = _SESSION_RE.fullmatch(cue)
            if match:
                session = int(match.group(1))
            continue
        # person cues: latin names (alice/bob/lina) or CJK names; skip dates
        if re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", cue):
            continue
        if cue and not person:
            person = cue
    return person, session


class EventChainIndex:
    """Successor links between chronologically ordered episodes.

    Legacy chains use explicit invalidation and ISO body dates. Opt-in
    source chains fingerprint event/grouping fields and share the temporal
    resolver. Only episodes with an unambiguous event date participate.
    """

    def __init__(self, backend: Backend, *, date_policy: str = "content",
                 event_timezone: tzinfo = timezone.utc) -> None:
        if date_policy not in ("content", "source"):
            raise ValueError("date_policy must be content or source")
        self.date_policy = date_policy
        self.event_timezone = event_timezone
        self._source_fingerprint = None
        self.backend = backend
        self._cache: dict[str, str | None] | None = None
        self._version = 0
        self._built_version = -1

    def invalidate(self) -> None:
        self._version += 1

    def _build(self) -> dict[str, str | None]:
        if self.date_policy == "source":
            return self._build_source()
        if self._cache is not None and self._version == self._built_version:
            return self._cache
        groups: dict[tuple[str, int | None], list[MemoryItem]] = {}
        for item in self.backend.list_items(kind=MemoryKind.EPISODIC):
            if item.status is not MemoryStatus.ACTIVE:
                continue
            person, session = _person_and_session(item)
            if not person or _date_of(item) is None:
                continue
            groups.setdefault((person, session), []).append(item)
        chain: dict[str, str | None] = {}
        for items in groups.values():
            items.sort(key=lambda i: (_date_of(i) or date.min, i.seq))
            for current, following in itertools.pairwise(items):
                chain[current.id] = following.id
        self._cache = chain
        self._built_version = self._version
        return chain

    def _build_source(self) -> dict[str, str | None]:
        # Source changes do not participate in the lexical revision token.
        # Fingerprint source and grouping fields so direct/backend updates
        # cannot leave a source timeline stale. This path scans the backend;
        # it makes no incremental-index or latency guarantee.
        rows = self.backend.list_items(kind=MemoryKind.EPISODIC)
        fingerprint = tuple((i.id, i.content, tuple(i.cues), i.kind, i.status,
                             i.seq, i.source.occurred_at) for i in rows)
        if (self._cache is not None and fingerprint == self._source_fingerprint
                and self._version == self._built_version):
            return self._cache
        groups = {}
        for item in rows:
            if item.status is not MemoryStatus.ACTIVE:
                continue
            person, session = _person_and_session(item)
            event = resolve_event_time(item, zone=self.event_timezone)
            if person and event.day is not None:
                groups.setdefault((person, session), []).append((event.order_key(self.event_timezone), item))
        chain = {}
        for events in groups.values():
            events.sort(key=lambda pair: (pair[0], pair[1].seq))
            for (_, current), (_, following) in itertools.pairwise(events):
                chain[current.id] = following.id
        self._cache = chain
        self._source_fingerprint = fingerprint
        self._built_version = self._version
        return chain

    def next_event_id(self, memory_id: str) -> str | None:
        return self._build().get(memory_id)

    def chain_length(self) -> int:
        return len(self._build())


__all__ = ["EventChainIndex", "_date_of", "_person_and_session"]
