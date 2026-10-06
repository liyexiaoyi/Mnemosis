"""Independent ranked fusion plus one-swap evidence composition.

Rank agreement and supplied support are proxies, not factual verification.
No retrieval, models, storage, feedback or default-policy side effects.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real

from .evidence_selection import EvidenceCandidate, QueryAspect
from .evidence_refinement import EvidenceRefinementReport, refine_evidence
from .ranked_evidence import (
    RankedChannel, RankedEvidenceReport, _sequence, select_ranked_evidence,
)


@dataclass(frozen=True, slots=True)
class RankedEvidenceRefinementReport:
    ranked_report: RankedEvidenceReport
    refinement: EvidenceRefinementReport


def refine_ranked_evidence(
    channels: Sequence[RankedChannel],
    aspects: Sequence[QueryAspect],
    *,
    support: Mapping[str, Mapping[str, Real]] | None = None,
    limit: int = 5,
    relevance_weight: Real = .5,
) -> RankedEvidenceRefinementReport:
    """Compose the existing public models with identical supplied inputs.

    The old ranked API/report is unchanged. Final IDs are available through
    refinement.selected_ids; ranked_report.selection retains the original
    greedy trace. Refine once in ranked candidate order, using fused relevance
    and the same raw aspect weights/support, capacity and relevance weight.
    All original validation/bounds apply, including failure and absent support.
    Support maps are copied before either stage, within the 100/32 bounds.
    Inputs must not be concurrently mutated. No support is inferred from text.

    To preserve the existing public models, refinement recomputes the greedy
    baseline. This costs an extra greedy pass; it does not perform a second
    swap round or extra retrieval. Both old reports and default recall remain
    unchanged. One-swap optimality is only over the original neighborhood.
    """
    _sequence(aspects, "aspects", 32)
    aspect_snapshot = tuple(aspects)
    support_snapshot = support
    if isinstance(support, Mapping):
        # Valid support cannot exceed the enabled union/aspect bounds. Check
        # before copying, rather than allocating an unbounded malformed map.
        if len(support) > 100:
            raise ValueError("support exceeds 100 candidates")
        copied = {}
        for memory_id, values in support.items():
            if isinstance(values, Mapping):
                if len(values) > 32:
                    raise ValueError("candidate support exceeds 32 aspects")
                copied[memory_id] = dict(values)
            else:
                # Let the original validator reject malformed nested values.
                copied[memory_id] = values
        support_snapshot = copied
    ranked = select_ranked_evidence(
        channels, aspect_snapshot, support=support_snapshot,
        limit=limit, relevance_weight=relevance_weight,
    )
    candidates = [
        EvidenceCandidate(memory_id, ranked.relevance_by_id[memory_id],
                          support_snapshot.get(memory_id, {}) if support_snapshot is not None else {})
        for memory_id in ranked.candidate_ids
    ]
    refinement = refine_evidence(
        candidates, aspect_snapshot, limit=ranked.selection.requested_limit,
        relevance_weight=relevance_weight,
    )
    return RankedEvidenceRefinementReport(ranked, refinement)


__all__ = ["RankedEvidenceRefinementReport", "refine_ranked_evidence"]
