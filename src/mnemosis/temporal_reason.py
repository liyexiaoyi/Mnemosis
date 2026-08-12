"""Time-cell anchored temporal reasoning.

Human principles (brain papers):

- *Time cells in the hippocampus* (Eichenbaum, 2014, Nat Rev Neurosci):
  hippocampal neurons fire at successive moments during an experience,
  giving the memory system an ordinal "when" map. Asking "after X on date D,
  what happened next?" is answered by *anchoring to D* and reading off the
  earliest future event, not by re-searching words.
- *Ramping cells in mPFC* (Cao, Bright & Howard, 2024, PNAS): prefrontal
  cells ramp as a remembered event in the past or future gets nearer. We
  emulate this as an exponential ramp: among events strictly after (before)
  the anchor date, the temporally nearest one gets the largest boost and
  farther events decay by half-life.
- *Transitive inference* (Zhang et al., 2022, NeuroImage meta-analysis):
  the hippocampus/PFC build a relational map that supports chaining
  A -> B -> C. We add a discounted second hop, so "two events later" can be
  completed from the schema even when the query shares no words with it.
- *Mental time travel* (Tulving, 1985): episodic memory is re-experiencing
  the past; both the "after" (future relative to anchor) and "before"
  (past relative to anchor) directions are supported.

Safety (round-8 lesson): the boost only fires when the query is *fully
anchored* - it must contain an explicit temporal marker (after/before/next/
之后/之前/...), an explicit anchor date, and at least one person cue. No
date, no marker, or no person -> no boost, so ordinary event/fact queries
are untouched.
"""

from __future__ import annotations

import re
from datetime import date

from .schema import _date_of, _person_and_session
from .types import MemoryItem, MemoryKind

_AFTER_MARKERS = (
    "after", "next", "then", "following", "followed", "subsequent",
    "later", "之后", "随后", "接着", "接下来", "后来", "再然后",
)
_BEFORE_MARKERS = (
    "before", "prior", "earlier", "previously", "preceding",
    "之前", "以前", "前面",
)
_ISO_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_HOP2_RE = re.compile(
    r"(?:two|2|second)\s+(?:events?|steps?|things?|days?|times?)"
    r"|(?:第二件|两件|两个|两次).{0,4}(?:事|事件|之后|後|后)"
)


def temporal_question_kind(query: str) -> str | None:
    """Return 'after' / 'before' for anchored ordering queries, else None."""
    lowered = query.lower()
    if any(marker in lowered for marker in _BEFORE_MARKERS):
        return "before"
    if any(marker in lowered for marker in _AFTER_MARKERS):
        return "after"
    return None


def anchor_dates(query_terms: set[str]) -> list[date]:
    """ISO dates found in the normalized query terms (zh dates included)."""
    out: list[date] = []
    for term in query_terms:
        match = _ISO_RE.fullmatch(term)
        if match:
            try:
                out.append(date(int(match.group(1)), int(match.group(2)),
                                int(match.group(3))))
            except ValueError:
                continue
    return out


def requested_hop(query: str) -> int:
    """Return 2 for 'two events after ...' style queries, else 1."""
    lowered = query.lower()
    if _HOP2_RE.search(lowered):
        return 2
    if "two events after" in lowered or "2 events after" in lowered:
        return 2
    return 1


def apply_time_cell_reasoning(
    scored: list[tuple[float, float, MemoryItem, list[str], bool]],
    candidates: list[MemoryItem],
    query: str,
    query_terms: set[str],
    *,
    boost_scale: float = 0.65,
    max_boost: float = 0.35,
    ramp_half_life_days: float = 7.0,
) -> None:
    """Boost anchored next/previous events for temporal-ordering queries.

    ``scored`` and ``candidates`` use the same item pool as
    ``DualTrackStore.recall``; ``scored`` is mutated in place and re-sorted.
    """
    kind = temporal_question_kind(query)
    if kind is None:
        return
    anchors = anchor_dates(query_terms)
    if not anchors:
        return
    anchor = anchors[0] if kind == "after" else anchors[-1]

    # One metadata pass: per-item (person, event date). Cues and content do
    # not change during a recall, so the regexes run once per candidate per
    # call (important at 10k+ scale).
    meta: dict[str, tuple[str | None, date | None]] = {}
    persons: set[str] = set()
    for item in candidates:
        if item.kind is not MemoryKind.EPISODIC:
            continue
        person, _ = _person_and_session(item)
        event_date = _date_of(item)
        meta[item.id] = (person, event_date)
        if person and person in query_terms:
            persons.add(person)
    if not persons:
        return

    hop = requested_hop(query)
    anchor_persons: set[str] = set()
    for item in candidates:
        if item.id not in meta:
            continue
        meta_person, meta_date = meta[item.id]
        if meta_person in persons and meta_date == anchor:
            anchor_persons.add(meta_person)

    # per-person temporal targets: nearest future / nearest past, and the
    # second future event for transitive two-hop questions
    nearest_future: dict[str, tuple[int, MemoryItem]] = {}
    second_future: dict[str, tuple[int, MemoryItem]] = {}
    nearest_past: dict[str, tuple[int, MemoryItem]] = {}
    anchor_items: dict[str, MemoryItem] = {}
    for item in candidates:
        if item.id not in meta:
            continue
        loop_person, event_date = meta[item.id]
        if loop_person not in persons or event_date is None:
            continue
        if event_date == anchor:
            anchor_items.setdefault(loop_person, item)
        if kind == "after" and event_date > anchor:
            delta = (event_date - anchor).days
            current = nearest_future.get(loop_person)
            if current is None or delta < current[0]:
                if current is not None:
                    second_future[loop_person] = current
                nearest_future[loop_person] = (delta, item)
            else:
                second = second_future.get(loop_person)
                if second is None or delta < second[0]:
                    second_future[loop_person] = (delta, item)
        elif kind == "before" and event_date < anchor:
            delta = (anchor - event_date).days
            current = nearest_past.get(loop_person)
            if current is None or delta < current[0]:
                nearest_past[loop_person] = (delta, item)

    decisive: dict[str, float] = {}
    conservative: dict[str, float] = {}
    second_target_ids: set[str] = set()
    # Decisive targets (the *answer* to an anchored ordering question) get a
    # flat, bounded lift independent of calendar distance: the mPFC ramping
    # signal marks "the next remembered event" whether it is 1 or 30 days
    # away. Farther non-target events keep the exponential decay instead.
    decisive_flat = min(max_boost * 1.6, 0.55)
    for person in persons:
        if kind == "after":
            targets: list[tuple[int, MemoryItem]] = []
            if hop >= 2 and person in second_future:
                _, item = second_future[person]
                targets.append(second_future[person])
                second_target_ids.add(item.id)
            if hop == 1 and person in nearest_future:
                targets.append(nearest_future[person])
            for delta, item in targets:
                raw = boost_scale * (0.5 ** (delta / ramp_half_life_days))
                boost = min(raw, max_boost)
                if person in anchor_persons and hop == 1:
                    # The anchor event is explicitly named in the query: lift
                    # it too so same-word events on other dates cannot crowd
                    # it out at scale; the successor gets a slightly smaller
                    # lift so the anchor stays first (anchor-first ordering).
                    if len(persons) == 1:
                        if person in anchor_items:
                            decisive[anchor_items[person].id] = decisive_flat
                        decisive[item.id] = decisive_flat * 0.8
                    else:
                        # multi-person: the anchor person's events are
                        # context, not the answer (the questioned person is)
                        conservative[item.id] = boost
                else:
                    decisive[item.id] = decisive_flat
        elif person in nearest_past:
            delta, item = nearest_past[person]
            raw = boost_scale * (0.5 ** (delta / ramp_half_life_days))
            decisive[item.id] = decisive_flat

    # farther events still get a conservative ramp (context, no re-rank)
    for item in candidates:
        if item.id not in meta:
            continue
        loop_person, event_date = meta[item.id]
        if loop_person not in persons or event_date is None:
            continue
        if item.id in decisive or item.id in conservative:
            continue
        if kind == "after" and event_date > anchor:
            delta = (event_date - anchor).days
        elif kind == "before" and event_date < anchor:
            delta = (anchor - event_date).days
        else:
            continue
        raw = boost_scale * (0.5 ** (delta / ramp_half_life_days))
        conservative[item.id] = min(raw, max_boost)

    if not decisive and not conservative:
        return
    by_id: dict[str, int] = {
        item.id: index for index, (_, _, item, _, _) in enumerate(scored)
    }
    by_item: dict[str, MemoryItem] = {item.id: item for item in candidates}

    def apply_boost(
        memory_id: str,
        boost: float,
        reason: str,
        *,
        force: bool,
    ) -> None:
        index = by_id.get(memory_id)
        if index is not None:
            old_score, overlap, item, reasons, matched = scored[index]
            if force or boost > old_score:
                scored[index] = (
                    old_score + boost,
                    overlap,
                    item,
                    reasons + [reason],
                    matched,
                )
            elif not any(reason in r for r in reasons):
                scored[index] = (
                    old_score,
                    overlap,
                    item,
                    reasons + [reason],
                    matched,
                )
        else:
            candidate = by_item.get(memory_id)
            if candidate is not None:
                scored.append((boost, 0.0, candidate, [reason], False))

    if kind == "after":
        future_reason = (
            "\u65f6\u95f4\u7ec6\u80de\u952e\u5b9a\uff08\u6700\u8fd1\u672a\u6765\u4e8b\u4ef6\uff09"
        )
        transitive_reason = (
            "\u4f20\u9012\u63a8\u7406\uff08\u4e8b\u4ef6\u94fe\u4e8c\u8df3\uff09"
        )
        for memory_id, boost in decisive.items():
            reason = (
                transitive_reason
                if memory_id in second_target_ids
                else future_reason
            )
            apply_boost(memory_id, boost, reason, force=True)
        for memory_id, boost in conservative.items():
            apply_boost(memory_id, boost, future_reason, force=False)
    else:
        past_reason = (
            "\u65f6\u95f4\u7ec6\u80de\u952e\u5b9a\uff08\u6700\u8fd1\u8fc7\u53bb\u4e8b\u4ef6\uff09"
        )
        for memory_id, boost in decisive.items():
            apply_boost(memory_id, boost, past_reason, force=True)
        for memory_id, boost in conservative.items():
            apply_boost(memory_id, boost, past_reason, force=False)
    scored.sort(key=lambda entry: entry[0], reverse=True)


__all__ = [
    "anchor_dates",
    "apply_time_cell_reasoning",
    "temporal_question_kind",
]
