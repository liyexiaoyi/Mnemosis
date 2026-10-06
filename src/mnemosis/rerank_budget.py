"""Constrained rerank membership, separate from relevance and evidence utility."""
from __future__ import annotations

from collections.abc import Sequence
from numbers import Integral

from .candidate_admission import _ranking, SEMANTIC_RESERVE

def reserve_semantic(
    primary_ids: Sequence[str],
    semantic_ids: Sequence[str],
    *,
    limit: int = 64,
) -> tuple[str, ...]:
    """Protect semantic prefix, retain the most primary IDs, preserve priority.

    Inputs are already admitted/scorable IDs. This reports membership, not
    scores or truth. For P and protected D, replacements are exactly
    max(0, |P union D| - limit); ties retain earlier primary IDs.
    """
    if isinstance(limit, bool) or not isinstance(limit, Integral):
        raise TypeError("limit must be an integer, not bool")
    if not 0 <= limit <= 64:
        raise ValueError("limit must be between 0 and 64")
    limit = int(limit)
    primary = _ranking(primary_ids, limit)
    semantic = _ranking(semantic_ids, SEMANTIC_RESERVE)[:limit]
    protected = set(semantic)
    retained = tuple(ident for ident in primary if ident not in protected)[:limit-len(semantic)]
    # Membership protects primary priority; this order has no score meaning.
    # Recall still embeds in its existing scored-item order.
    return retained + semantic
