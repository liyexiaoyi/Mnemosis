"""Explicit-input working-memory selection; scores are proxy utility, not truth.

No retrieval, model, storage or feedback side effects. Missing support means
not supplied, and a coverage gap is not a verified absence of evidence.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
import math
from numbers import Integral, Real


@dataclass(frozen=True, slots=True)
class QueryAspect:
    aspect_id: str
    weight: float = 1.0


@dataclass(frozen=True, slots=True)
class EvidenceCandidate:
    memory_id: str
    relevance: float
    support: Mapping[str, float]


@dataclass(frozen=True, slots=True)
class SelectionStep:
    memory_id: str
    relevance_gain: float
    coverage_gain: float
    total_gain: float
    objective_after: float


@dataclass(frozen=True, slots=True)
class EvidenceSelectionReport:
    selected_ids: tuple[str, ...]
    steps: tuple[SelectionStep, ...]
    aspect_coverage: dict[str, float]
    normalized_aspect_weights: dict[str, float]
    uncovered_aspect_ids: tuple[str, ...]
    partial_aspect_ids: tuple[str, ...]
    relevance_component: float
    coverage_component: float
    objective: float
    requested_limit: int
    candidate_count: int


def _identifier(value: str, name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    if not value or value != value.strip():
        raise ValueError(f"{name} must be nonempty and trimmed")
    return value


def _real(value: Real, name: str, *, unit: bool = False) -> Real:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise TypeError(f"{name} must be a real number, not bool")
    # Compare before float conversion: finite integer weights can exceed
    # binary64 while their ratios are representable after max scaling.
    if value != value or value == math.inf or value == -math.inf:
        raise ValueError(f"{name} must be finite")
    if value < 0 or (unit and value > 1):
        raise ValueError(f"{name} outside its allowed range")
    return value


def _sequence(value: Sequence, name: str, maximum: int) -> None:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise TypeError(f"{name} must be a sequence")
    if len(value) > maximum:
        raise ValueError(f"{name} exceeds {maximum}")


def _exact_weight(value: Real) -> Fraction:
    # as_integer_ratio also supports NumPy float scalars on Python 3.10,
    # where Fraction does not yet accept arbitrary ratio-bearing objects.
    ratio = getattr(value, "as_integer_ratio", None)
    return Fraction(*ratio()) if ratio is not None else Fraction(value)


def _scaled_weight(value: Real, maximum: Real) -> float:
    try:
        return float(value / maximum)
    except OverflowError:
        # A mixed float / large rational division can convert the denominator
        # before taking a bounded ratio. Take that ratio exactly instead.
        return float(_exact_weight(value) / _exact_weight(maximum))


def _score_subset(
    candidates: Sequence[EvidenceCandidate],
    normalized_weights: Mapping[str, float],
    selected_indices: Sequence[int],
    *,
    limit: int,
    relevance_weight: float,
) -> tuple[float, float, float]:
    """Components for validated, snapshotted inputs and a feasible subset."""
    if limit == 0:
        return 0.0, 0.0, 0.0
    relevance = math.fsum(candidates[i].relevance / limit for i in selected_indices)
    coverage = math.fsum(
        weight * max((candidates[i].support.get(aspect, 0.0)
                      for i in selected_indices), default=0.0)
        for aspect, weight in normalized_weights.items()
    )
    objective = math.fsum((relevance_weight * relevance,
                          (1.0 - relevance_weight) * coverage))
    return relevance, coverage, objective


def _report_unit(value: float) -> float:
    """Remove only bounded roundoff, never conceal a substantive violation."""
    if not -1e-12 <= value <= 1.0 + 1e-12:
        raise ArithmeticError("proxy score outside its mathematical range")
    return max(0.0, min(1.0, value))


def select_evidence(
    candidates: Sequence[EvidenceCandidate],
    aspects: Sequence[QueryAspect],
    *,
    limit: int = 5,
    relevance_weight: float = .5,
) -> EvidenceSelectionReport:
    """Greedy marginal relevance/K plus saturated supplied-aspect coverage.

    At most 100 candidates and 32 aspects; limit is 0..100. All inputs are
    validated even for zero capacity. Empty aspects require weight=1.
    Only positive gains are selected; exact ties keep input order. This is
    a cardinality-constrained proxy objective, not a token budget, factual
    confidence, task sufficiency decision or always-optimal selection.
    """
    if isinstance(limit, bool) or not isinstance(limit, Integral):
        raise TypeError("limit must be an integer, not bool")
    if not 0 <= limit <= 100:
        raise ValueError("limit must be between 0 and 100")
    limit = int(limit)
    lam = float(_real(relevance_weight, "relevance_weight", unit=True))
    _sequence(candidates, "candidates", 100)
    _sequence(aspects, "aspects", 32)

    raw_weights: dict[str, Real] = {}
    for aspect in aspects:
        if not isinstance(aspect, QueryAspect):
            raise TypeError("aspects must contain QueryAspect values")
        key = _identifier(aspect.aspect_id, "aspect_id")
        if key in raw_weights:
            raise ValueError("duplicate aspect_id")
        raw_weights[key] = _real(aspect.weight, "aspect weight")
    if not raw_weights and lam != 1.0:
        raise ValueError("empty aspects require pure relevance weight=1")
    positive = {key for key, weight in raw_weights.items() if weight > 0}
    if raw_weights and not positive:
        raise ValueError("at least one aspect weight must be positive")
    weights: dict[str, float] = {}
    if raw_weights:
        try:
            maximum = max(raw_weights.values())
        except OverflowError:
            # Some Real scalars coerce a large integer during comparison.
            maximum = max(raw_weights.values(), key=_exact_weight)
        scaled = {key: _scaled_weight(weight, maximum) for key, weight in raw_weights.items()}
        total = math.fsum(scaled.values())
        weights = {key: value / total for key, value in scaled.items()}

    snapshot: list[EvidenceCandidate] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, EvidenceCandidate):
            raise TypeError("candidates must contain EvidenceCandidate values")
        key = _identifier(candidate.memory_id, "memory_id")
        if key in seen:
            raise ValueError("duplicate memory_id")
        seen.add(key)
        relevance = float(_real(candidate.relevance, "relevance", unit=True))
        if not isinstance(candidate.support, Mapping):
            raise TypeError("support must be a mapping")
        support = {}
        for aspect, value in candidate.support.items():
            if aspect not in raw_weights:
                raise ValueError("unknown support aspect_id")
            support[aspect] = float(_real(value, "support", unit=True))
        snapshot.append(EvidenceCandidate(key, relevance, support))

    covered = dict.fromkeys(weights, 0.0)
    selected: list[int] = []
    selected_set: set[int] = set()
    steps: list[SelectionStep] = []
    accumulated = 0.0
    for _ in range(min(limit, len(snapshot))):
        best = None
        best_gain = 0.0
        best_relevance = best_coverage = 0.0
        for index, candidate in enumerate(snapshot):
            if index in selected_set:
                continue
            relevance_gain = lam * candidate.relevance / limit
            coverage_gain = (1.0 - lam) * math.fsum(
                weight * max(0.0, candidate.support.get(aspect, 0.0) - covered[aspect])
                for aspect, weight in weights.items()
            )
            gain = math.fsum((relevance_gain, coverage_gain))
            if gain > best_gain:
                best, best_gain = index, gain
                best_relevance, best_coverage = relevance_gain, coverage_gain
        if best is None:
            break
        selected.append(best)
        selected_set.add(best)
        chosen = snapshot[best]
        for aspect in covered:
            covered[aspect] = max(covered[aspect], chosen.support.get(aspect, 0.0))
        accumulated = math.fsum((accumulated, best_gain))
        steps.append(SelectionStep(chosen.memory_id, best_relevance, best_coverage,
                                   best_gain, _report_unit(accumulated)))
    relevance, coverage, objective = _score_subset(
        snapshot, weights, selected, limit=limit, relevance_weight=lam
    )
    return EvidenceSelectionReport(
        selected_ids=tuple(snapshot[i].memory_id for i in selected),
        steps=tuple(steps), aspect_coverage=covered,
        normalized_aspect_weights=weights,
        uncovered_aspect_ids=tuple(a for a in covered if a in positive and covered[a] == 0),
        partial_aspect_ids=tuple(a for a in covered if a in positive and 0 < covered[a] < 1),
        relevance_component=_report_unit(relevance),
        coverage_component=_report_unit(coverage), objective=_report_unit(objective),
        requested_limit=limit, candidate_count=len(snapshot),
    )


__all__ = ["QueryAspect", "EvidenceCandidate", "SelectionStep", "EvidenceSelectionReport", "select_evidence"]
