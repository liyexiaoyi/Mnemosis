"""Bounded quota admission, separate from relevance and evidence selection."""
from __future__ import annotations

from collections.abc import Sequence
import math
from numbers import Real

from .types import MemoryStatus

ADMISSION_LIMIT = 100
LEXICAL_RESERVE = 64
SEMANTIC_RESERVE = 36
INDEX_LOOKUP_LIMIT = 100


def _ranking(values: Sequence[str], maximum: int) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)) or not isinstance(values, Sequence):
        raise TypeError("rankings must be sequences")
    if len(values) > maximum:
        raise ValueError("ranking exceeds its admission budget")
    copied = tuple(values)
    for ident in copied:
        if not isinstance(ident, str):
            raise TypeError("candidate ID must be a string")
        if not ident or ident != ident.strip():
            raise ValueError("candidate ID must be nonempty and trimmed")
    if len(set(copied)) != len(copied):
        raise ValueError("ranking contains duplicate IDs")
    return copied


def quota_admission(
    lexical_ids: Sequence[str], semantic_ids: Sequence[str],
) -> tuple[str, ...]:
    """Protect lexical64 and semantic36, then refill from lexical ranks.

    The result is a membership/order report, not a score or truth estimate.
    Both input rankings are bounded; cross-channel overlaps count once.
    """
    lexical = _ranking(lexical_ids, ADMISSION_LIMIT)
    semantic = _ranking(semantic_ids, SEMANTIC_RESERVE)
    selected = list(lexical[:LEXICAL_RESERVE])
    seen = set(selected)
    for ident in semantic + lexical[LEXICAL_RESERVE:]:
        if ident not in seen and len(selected) < ADMISSION_LIMIT:
            selected.append(ident)
            seen.add(ident)
    return tuple(selected)


def _index_candidates(backend, hits, kind, excluded):
    """Validate one bounded index result and filter before semantic quota."""
    if isinstance(hits, (str, bytes)) or not isinstance(hits, Sequence):
        raise TypeError("index hits must be a sequence")
    if len(hits) > INDEX_LOOKUP_LIMIT:
        raise ValueError("index returned more than 100 hits")
    ordered = []
    seen = set()
    for hit in hits:
        if (isinstance(hit, (str, bytes)) or not isinstance(hit, Sequence)
                or len(hit) != 2):
            raise ValueError("index hit must be an ID/score pair")
        ident, score = hit
        _ranking([ident], 1)
        if isinstance(score, bool) or not isinstance(score, Real):
            raise TypeError("index score must be real")
        try:
            finite = math.isfinite(score)
        except OverflowError:
            finite = False
        if not finite:
            raise ValueError("index score must be finite")
        if ident not in seen and ident not in excluded:
            ordered.append(ident)
            seen.add(ident)
    items = {item.id: item for item in backend.get_many(ordered)}
    eligible = [items[ident] for ident in ordered if ident in items
                and items[ident].status is MemoryStatus.ACTIVE
                and (kind is None or items[ident].kind is kind)]
    return eligible[:SEMANTIC_RESERVE]
