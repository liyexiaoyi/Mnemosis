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
    # Foreign scalars can divide in float16/32 before float() is applied.
    # Form their bounded ratio exactly to avoid irreversible rounding.
    if any(type(operand) not in (int, float, Fraction)
           and callable(getattr(operand, "as_integer_ratio", None))
           for operand in (value, maximum)):
        return float(_exact_weight(value) / _exact_weight(maximum))
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


@dataclass(frozen=True, slots=True)
class RequiredEvidenceReport:
    """Feasibility refers only to supplied support, never semantic truth.

    Exact Fraction coverage avoids threshold rounding. An absent selection is
    no feasible witness, not an incomplete selection labeled as sufficient.
    """

    baseline: EvidenceSelectionReport
    selection: EvidenceSelectionReport | None
    status: str
    optimality: str
    required_thresholds: dict[str, Fraction]
    pool_coverage: dict[str, Fraction]
    required_coverage: dict[str, Fraction] | None
    completeness: Fraction | None
    support_state: str
    missing_support_pairs: tuple[tuple[str, str], ...]
    visited_nodes: int
    search_budget: int
    search_complete: bool


def _selection_for_subset(
    candidates: Sequence[EvidenceCandidate],
    aspects: Sequence[QueryAspect],
    baseline: EvidenceSelectionReport,
    indices: tuple[int, ...],
    lam: float,
) -> EvidenceSelectionReport:
    """Replay marginal components in input order; these are not search steps."""
    weights = baseline.normalized_aspect_weights
    covered = dict.fromkeys(weights, 0.0)
    steps = []
    previous_relevance = previous_coverage = previous_objective = 0.0
    for position, index in enumerate(indices):
        relevance, coverage, objective = _score_subset(
            candidates, weights, indices[:position + 1],
            limit=baseline.requested_limit, relevance_weight=lam,
        )
        steps.append(SelectionStep(
            candidates[index].memory_id,
            lam * (relevance - previous_relevance),
            (1 - lam) * (coverage - previous_coverage),
            objective - previous_objective, _report_unit(objective),
        ))
        previous_relevance, previous_coverage, previous_objective = relevance, coverage, objective
        for aspect in covered:
            covered[aspect] = max(covered[aspect], candidates[index].support.get(aspect, 0.0))
    positive = {a.aspect_id for a in aspects if a.weight > 0}
    return EvidenceSelectionReport(
        tuple(candidates[i].memory_id for i in indices), tuple(steps), covered,
        dict(weights), tuple(a for a in covered if a in positive and covered[a] == 0),
        tuple(a for a in covered if a in positive and 0 < covered[a] < 1),
        _report_unit(previous_relevance), _report_unit(previous_coverage),
        _report_unit(previous_objective), baseline.requested_limit, len(candidates),
    )


def select_required_evidence(
    candidates: Sequence[EvidenceCandidate],
    aspects: Sequence[QueryAspect],
    *,
    required_aspects: Mapping[str, Real] | Sequence[str],
    limit: int = 5,
    relevance_weight: float = .5,
    search_budget: int = 10000,
) -> RequiredEvidenceReport:
    """Bounded subset search under explicit required-support thresholds.

    Uses the existing U objective and capacity, with exact raw threshold
    comparisons. A sequence of required IDs uses threshold 1; a mapping
    provides per-role thresholds in (0,1]. Empty requirements delegate to
    select_evidence. No recall, storage, inference or support generation.

    Budget counts DFS nodes, including pruned nodes (0..100000), not seconds.
    A feasible incumbent survives exhaustion; its optimality is not proven.
    Infeasible means proved for the supplied inputs; undetermined means no
    witness yet. Complete enumeration maximizes the existing float-computed
    proxy utility, not an exact real-valued objective or factual correctness.
    Inputs must not be modified concurrently during this call.
    """
    if isinstance(search_budget, bool) or not isinstance(search_budget, Integral):
        raise TypeError("search_budget must be an integer, not bool")
    if not 0 <= search_budget <= 100000:
        raise ValueError("search_budget must be between 0 and 100000")
    search_budget = int(search_budget)
    if isinstance(required_aspects, Mapping):
        if len(required_aspects) > 32:
            raise ValueError("required_aspects exceeds 32")
        required = dict(required_aspects)
    else:
        _sequence(required_aspects, "required_aspects", 32)
        required = {}
        for value in required_aspects:
            key = _identifier(value, "required aspect_id")
            if key in required:
                raise ValueError("duplicate required aspect_id")
            required[key] = 1
    # All original validation runs even with zero capacity or empty roles.
    baseline = select_evidence(candidates, aspects, limit=limit, relevance_weight=relevance_weight)
    thresholds = {}
    for aspect, value in required.items():
        key = _identifier(aspect, "required aspect_id")
        if key not in baseline.normalized_aspect_weights:
            raise ValueError("unknown required aspect_id")
        raw = _real(value, "required threshold", unit=True)
        if raw == 0:
            raise ValueError("required threshold must be strictly positive")
        thresholds[key] = _exact_weight(raw)
    if not thresholds:
        return RequiredEvidenceReport(baseline, baseline, "not_applicable", "not_applicable",
                                      {}, {}, None, None, "not_applicable", (), 0,
                                      search_budget, True)

    # Snapshot raw support before binary64 conversion. Max-threshold coverage
    # is exactly a set-cover mask: a role needs at least one qualifying record.
    raw_support = [{a: _exact_weight(c.support[a]) for a in thresholds if a in c.support}
                   for c in candidates]
    missing = tuple((c.memory_id, a) for c in candidates for a in thresholds if a not in c.support)
    supplied = len(candidates) * len(thresholds) - len(missing)
    support_state = "absent" if supplied == 0 else "partial" if missing else "complete"
    pool = {a: max((s.get(a, Fraction(0)) for s in raw_support), default=Fraction(0))
            for a in thresholds}
    masks = [sum(1 << j for j, (a, tau) in enumerate(thresholds.items())
                 if s.get(a, Fraction(0)) >= tau) for s in raw_support]
    full = (1 << len(thresholds)) - 1
    snapshot = [EvidenceCandidate(c.memory_id, float(c.relevance),
                                 {a: float(s) for a, s in c.support.items()}) for c in candidates]
    lam = float(relevance_weight)
    capacity = baseline.requested_limit
    best = None
    best_objective = -1.0
    baseline_indices = tuple(i for i, c in enumerate(snapshot) if c.memory_id in baseline.selected_ids)
    baseline_mask = 0
    for i in baseline_indices:
        baseline_mask |= masks[i]
    if baseline_mask == full:
        best = baseline_indices
        best_objective = _score_subset(snapshot, baseline.normalized_aspect_weights, best,
                                       limit=capacity, relevance_weight=lam)[2]

    visited = 0
    complete = False
    if capacity == 0 or any(pool[a] < tau for a, tau in thresholds.items()):
        complete = True
    else:
        # Coverage-first order makes early witnesses more likely; tie decisions
        # below use original input indices, independent of traversal order.
        order = sorted(range(len(snapshot)), key=lambda i: (-masks[i].bit_count(),
                                                           -snapshot[i].relevance, i))
        suffix = [0] * (len(order) + 1)
        for p in range(len(order) - 1, -1, -1):
            suffix[p] = suffix[p + 1] | masks[order[p]]
        stack = [(0, (), 0)]
        while stack and visited < search_budget:
            p, chosen, mask = stack.pop()
            visited += 1
            if mask == full:
                canonical = tuple(sorted(chosen))
                objective = _score_subset(snapshot, baseline.normalized_aspect_weights, canonical,
                                          limit=capacity, relevance_weight=lam)[2]
                if (objective > best_objective or
                    (objective == best_objective and best is not None and
                     (len(canonical), canonical) < (len(best), best))):
                    best, best_objective = canonical, objective
            slots = capacity - len(chosen)
            if slots == 0 or p == len(order) or (mask | suffix[p]) != full:
                continue
            if mask != full:
                uncovered = full ^ mask
                maximum_gain = max((masks[i] & uncovered).bit_count() for i in order[p:])
                # Safe lower bound on needed slots; overlap can only worsen it.
                if maximum_gain == 0 or uncovered.bit_count() > slots * maximum_gain:
                    continue
            i = order[p]
            stack.append((p + 1, chosen, mask))
            stack.append((p + 1, chosen + (i,), mask | masks[i]))
        complete = not stack

    selection = None
    coverage = None
    completeness = None
    if best is not None:
        selection = _selection_for_subset(snapshot, aspects, baseline, best, lam)
        coverage = {a: max((raw_support[i].get(a, Fraction(0)) for i in best), default=Fraction(0))
                    for a in thresholds}
        completeness = min(min(Fraction(1), coverage[a] / tau) for a, tau in thresholds.items())
    status = "feasible" if best is not None else "infeasible" if complete else "undetermined"
    optimality = "optimal" if best is not None and complete else "not_proven" if best is not None else "not_applicable"
    return RequiredEvidenceReport(baseline, selection, status, optimality, thresholds, pool,
                                  coverage, completeness, support_state, missing, visited,
                                  search_budget, complete)


__all__ = ["QueryAspect", "EvidenceCandidate", "SelectionStep", "EvidenceSelectionReport",
           "select_evidence", "RequiredEvidenceReport", "select_required_evidence"]
