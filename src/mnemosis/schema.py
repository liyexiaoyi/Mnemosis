"""Event-chain (schema) memory: linking ordered episodes into a timeline.

Human principle (Gilboa & Marlatte, 2017; Bartlett, 1932): experiences are
stored not as isolated snapshots but as parts of *schematic sequences* —
event schemas ("what typically happens next"). Mnemosis keeps a lightweight
event-chain index: episodes sharing a person + session are ordered by date,
and each event knows its chronological successor. Recall can then follow the
chain, the same way "after X, what happened?" is answered from a script.
"""

from __future__ import annotations

import re
from datetime import date

from .backend import Backend
from .types import MemoryItem, MemoryKind, MemoryStatus


_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_SESSION_RE = re.compile(r"session(\d+)")


def _date_of(item: MemoryItem) -> date | None:
    """Extract the event date from content or cues, if present."""
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

    The chain is derived lazily from the backend, so it never goes stale
    (memory updates are reflected on the next lookup). Only episodes with a
    parseable date participate.
    """

    def __init__(self, backend: Backend) -> None:
        self.backend = backend
        self._cache: dict[str, str | None] | None = None

    def invalidate(self) -> None:
        self._cache = None

    def _build(self) -> dict[str, str | None]:
        if self._cache is not None:
            return self._cache
        groups: dict[tuple[str, int | None], list[MemoryItem]] = {}
        for item in self.backend.list(kind=MemoryKind.EPISODIC):
            if item.status is not MemoryStatus.ACTIVE:
                continue
            person, session = _person_and_session(item)
            if not person or _date_of(item) is None:
                continue
            groups.setdefault((person, session), []).append(item)
        chain: dict[str, str | None] = {}
        for items in groups.values():
            items.sort(key=lambda i: (_date_of(i) or date.min, i.seq))
            for current, following in zip(items, items[1:]):
                chain[current.id] = following.id
        self._cache = chain
        return chain

    def next_event_id(self, memory_id: str) -> str | None:
        return self._build().get(memory_id)

    def chain_length(self) -> int:
        return len(self._build())


__all__ = ["EventChainIndex", "_date_of", "_person_and_session"]
