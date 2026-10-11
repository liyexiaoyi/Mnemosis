"""One optional best swap of explicit evidence; proxy utility is not truth.

Independent of recall, storage and feedback. The default greedy selector is
unchanged. One round improves its original neighborhood, not a global optimum
or necessarily a local optimum of the resulting subset.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .evidence_selection import (
    EvidenceCandidate, EvidenceSelectionReport, QueryAspect,
    _RealValue, _report_unit, _score_subset, select_evidence, _sequence,
)


@dataclass(frozen=True, slots=True)
class EvidenceSwap:
    removed_id: str
    added_id: str
    objective_before: float
    objective_after: float
    objective_gain: float


@dataclass(frozen=True, slots=True)
class EvidenceRefinementReport:
    original_report: EvidenceSelectionReport
    selected_ids: tuple[str, ...]
    swap: EvidenceSwap | None
    examined_swaps: int
    aspect_coverage: dict[str, float]
    uncovered_aspect_ids: tuple[str, ...]
    partial_aspect_ids: tuple[str, ...]
    relevance_component: float
    coverage_component: float
    objective: float


def refine_evidence(
    candidates: Sequence[EvidenceCandidate],
    aspects: Sequence[QueryAspect],
    *,
    limit: int = 5,
    relevance_weight: _RealValue = .5,
) -> EvidenceRefinementReport:
    """Original greedy selection plus one best strictly improving swap.

    Same explicit inputs, normalization and bounds as select_evidence. Each
    selected position is paired with each originally unselected candidate;
    exact computed ties retain selected-position then candidate input order.
    Full subset scores are recomputed with the original math.fsum objective.
    No additions, deletions or second round; replacement retains its position.
    At most k*(n-k)<=2500 pairs, or <=475 for capacity5 and n<=100. Scoring
    costs O(k*number_of_aspects) per pair. The original greedy steps stay in
    original_report and must not be treated as final refinement steps.
    """
    _sequence(candidates, "candidates", 100)
    _sequence(aspects, "aspects", 32)
    # Copy supplied mappings once before validation/selection so both stages
    # use the same evidence. Preserve malformed values for public validation.
    snapshot = tuple(
        EvidenceCandidate(c.memory_id, c.relevance, dict(c.support))
        if isinstance(c, EvidenceCandidate) and isinstance(c.support, Mapping)
        else c for c in candidates
    )
    aspect_snapshot = tuple(aspects)
    original = select_evidence(snapshot, aspect_snapshot, limit=limit,
                               relevance_weight=relevance_weight)
    # Only convert after the existing validator has checked all values,
    # including zero capacity. Keep its carefully normalized aspect weights.
    validated = tuple(EvidenceCandidate(c.memory_id, float(c.relevance),
                                       {a: float(v) for a, v in c.support.items()})
                      for c in snapshot)
    capacity = original.requested_limit
    lam = float(relevance_weight)
    weights = original.normalized_aspect_weights
    by_id = {c.memory_id: i for i, c in enumerate(validated)}
    selected = [by_id[key] for key in original.selected_ids]
    selected_set = set(selected)
    unselected = [i for i in range(len(validated)) if i not in selected_set]
    relevance, coverage, objective = _score_subset(
        validated, weights, selected, limit=capacity, relevance_weight=lam)
    original_objective = objective
    best_indices = selected
    best_pair = None
    examined = 0
    # Every alternative starts from the original subset, never the last best.
    for pos, removed in enumerate(selected):
        for added in unselected:
            alternative = selected[:pos] + [added] + selected[pos+1:]
            next_relevance, next_coverage, next_objective = _score_subset(
                validated, weights, alternative, limit=capacity,
                relevance_weight=lam)
            examined += 1
            if next_objective > objective:
                best_indices = alternative
                best_pair = removed, added
                relevance, coverage, objective = next_relevance, next_coverage, next_objective
    covered = {
        aspect: max((validated[i].support.get(aspect, 0.0) for i in best_indices), default=0.0)
        for aspect in weights
    }
    positive = {a.aspect_id for a in aspect_snapshot if a.weight > 0}
    swap = None
    if best_pair is not None:
        removed, added = best_pair
        swap = EvidenceSwap(validated[removed].memory_id, validated[added].memory_id,
                            _report_unit(original_objective), _report_unit(objective),
                            objective - original_objective)
    return EvidenceRefinementReport(
        original_report=original,
        selected_ids=tuple(validated[i].memory_id for i in best_indices),
        swap=swap, examined_swaps=examined, aspect_coverage=covered,
        uncovered_aspect_ids=tuple(a for a in covered if a in positive and covered[a] == 0),
        partial_aspect_ids=tuple(a for a in covered if a in positive and 0 < covered[a] < 1),
        relevance_component=_report_unit(relevance),
        coverage_component=_report_unit(coverage), objective=_report_unit(objective),
    )


__all__ = ["EvidenceSwap", "EvidenceRefinementReport", "refine_evidence"]
