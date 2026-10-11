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
import threading
from datetime import date, datetime, timezone, tzinfo

from .backend import Backend
from .event_time import resolve_event_time
from .types import MemoryItem, MemoryKind, MemoryStatus

_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")
_SESSION_RE = re.compile(r"session(\d+)")

_SourceGroup = tuple[str, int | None]
_SourceOrder = tuple[datetime, int]
_SourceFingerprint = tuple[tuple[str, str, tuple[str, ...], MemoryKind, MemoryStatus, int, str | None], ...]


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
    source chains synchronize event-field revisions when provided by the
    backend, otherwise fingerprint mutable records. Only episodes with an
    unambiguous event date participate. Query timezones are cache boundaries.
    """

    def __init__(self, backend: Backend, *, date_policy: str = "content",
                 event_timezone: tzinfo = timezone.utc) -> None:
        if date_policy not in ("content", "source"):
            raise ValueError("date_policy must be content or source")
        self.date_policy = date_policy
        self.event_timezone = event_timezone
        self._source_fingerprint: _SourceFingerprint | None = None
        self._source_token: object | None = None
        self._source_zone: tzinfo | None = None
        self._source_groups: dict[_SourceGroup, dict[str, _SourceOrder]] = {}
        self._source_membership: dict[str, _SourceGroup] = {}
        self._lock = threading.RLock()
        self.backend = backend
        self._cache: dict[str, str | None] | None = None
        self._version = 0
        self._built_version = -1

    def invalidate(self) -> None:
        with self._lock:
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

    def _source_entry(self, item: MemoryItem) -> tuple[_SourceGroup, _SourceOrder] | None:
        if item.status is not MemoryStatus.ACTIVE or item.kind is not MemoryKind.EPISODIC:
            return None
        person, session = _person_and_session(item)
        event = resolve_event_time(item, zone=self.event_timezone)
        if not person or event.day is None:
            return None
        return (person, session), (event.order_key(self.event_timezone), item.seq)

    @staticmethod
    def _group_edges(events):
        ordered = sorted(events, key=events.__getitem__)
        return dict(itertools.pairwise(ordered))

    def _update_source_groups(self, changed):
        # Resolve first: a failed read/resolver cannot publish a half-updated
        # index. Removed/recycled/semantic/unknown-date rows leave their group.
        entries = {i.id: self._source_entry(i) for i in self.backend.get_many(changed)}
        affected = {self._source_membership[i] for i in changed if i in self._source_membership}
        affected.update(entry[0] for entry in entries.values() if entry is not None)
        groups = {key: dict(self._source_groups.get(key, {})) for key in affected}
        for ident in changed:
            old = self._source_membership.get(ident)
            if old is not None:
                groups[old].pop(ident, None)
        for ident, entry in entries.items():
            if entry is not None:
                key, order = entry
                groups[key][ident] = order
        edges = {}
        for events in groups.values():
            edges.update(self._group_edges(events))
        cache = self._cache
        assert cache is not None  # updates are only used for a reusable cache
        # In the unlikely event publication raises, the next query rebuilds
        # rather than reading a partial index under the previous token.
        self._cache = None
        for key, events in groups.items():
            for ident in self._source_groups.get(key, {}):
                cache.pop(ident, None)
            if events:
                self._source_groups[key] = events
            else:
                self._source_groups.pop(key, None)
        for ident in changed:
            self._source_membership.pop(ident, None)
        for ident, entry in entries.items():
            if entry is not None:
                self._source_membership[ident] = entry[0]
        cache.update(edges)
        self._cache = cache

    def _build_source(self) -> dict[str, str | None]:
        token = self.backend.event_revision_token()
        reusable = (self._cache is not None and self._version == self._built_version
                    and self._source_zone == self.event_timezone)
        if reusable and token is not None and self._source_token == token:
            assert self._cache is not None
            return self._cache
        if reusable and token is not None and self._source_token is not None:
            changed = self.backend.event_changes_since(self._source_token)
            if changed is not None:
                self._update_source_groups(changed)
                if self.backend.event_revision_token() != token:
                    # A racing delta may mix old group members with new rows.
                    # Clear the token and take one full row snapshot instead;
                    # that path never retries, so continuous writers cannot
                    # cause unbounded recursion or publish a false cache tag.
                    self._source_token = None
                    return self._build_source()
                self._source_token = token
                assert self._cache is not None
                return self._cache
        rows = self.backend.list_items(kind=MemoryKind.EPISODIC)
        fingerprint = None
        if token is None:
            # Dict/custom backends may expose directly mutable nested values.
            # datetime equality can ignore fold for the same tzinfo object.
            # Freeze the offset-bearing representation, not a datetime alias.
            fingerprint = tuple((i.id, i.content, tuple(i.cues), i.kind, i.status,
                                 i.seq, stamp.isoformat() if (stamp := i.source.occurred_at) is not None else None)
                                for i in rows)
            if reusable and fingerprint == self._source_fingerprint:
                assert self._cache is not None
                return self._cache
        groups: dict[_SourceGroup, dict[str, _SourceOrder]] = {}
        membership: dict[str, _SourceGroup] = {}
        for item in rows:
            entry = self._source_entry(item)
            if entry is not None:
                key, order = entry
                groups.setdefault(key, {})[item.id] = order
                membership[item.id] = key
        chain = {}
        for events in groups.values():
            chain.update(self._group_edges(events))
        self._source_groups, self._source_membership = groups, membership
        self._cache = chain
        self._source_fingerprint = fingerprint
        self._source_token = token if token is not None and self.backend.event_revision_token() == token else None
        self._source_zone = self.event_timezone
        self._built_version = self._version
        return chain

    def next_event_id(self, memory_id: str) -> str | None:
        with self._lock:
            return self._build().get(memory_id)

    def chain_length(self) -> int:
        with self._lock:
            return len(self._build())


__all__ = ["EventChainIndex", "_date_of", "_person_and_session"]
