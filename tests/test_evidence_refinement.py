"""Catch missed/bad swaps, extra rounds, input mutation and validation bypasses."""
from copy import deepcopy
from fractions import Fraction as F
import importlib
import math
import random
from types import MappingProxyType

import pytest
from mnemosis.evidence_selection import EvidenceCandidate as C, QueryAspect as A, select_evidence


@pytest.fixture
def refine():
    try:
        return importlib.import_module("mnemosis.evidence_refinement").refine_evidence
    except ModuleNotFoundError as exc:
        if exc.name != "mnemosis.evidence_refinement":
            raise
        def missing(*args, **kwargs):
            pytest.fail("approved one-swap evidence refinement is not implemented")
        return missing


def counterexample():
    return ([C("A", .6, {str(a): 1. for a in (1, 2, 3, 4)}),
             C("B", .6, {str(a): 1. for a in (1, 2, 5)}),
             C("C", .6, {str(a): 1. for a in (3, 4, 6)})],
            [A(str(a)) for a in range(1, 7)])


def test_best_swap_repairs_greedy_trap_and_keeps_original_steps(refine):
    candidates, aspects = counterexample()
    report = refine(candidates, aspects, limit=2)
    assert report.original_report == select_evidence(candidates, aspects, limit=2)
    assert report.original_report.selected_ids == ("A", "B")
    assert tuple(s.memory_id for s in report.original_report.steps) == ("A", "B")
    assert report.selected_ids == ("C", "B")  # replace at the removed position
    assert report.swap.removed_id == "A" and report.swap.added_id == "C"
    assert report.examined_swaps == 2
    assert report.objective == pytest.approx(float(F(4, 5)), abs=1e-15)
    assert report.swap.objective_gain == pytest.approx(float(F(1, 12)), abs=1e-15)
    assert report.aspect_coverage == {str(a): 1. for a in range(1, 7)}
    assert report.uncovered_aspect_ids == report.partial_aspect_ids == ()
    assert report.relevance_component == pytest.approx(.6)
    assert report.coverage_component == 1.


def test_no_improvement_preserves_selection_and_does_not_swap_ties(refine):
    candidates = [C("A", .8, {"x": 1}), C("B", .8, {"x": 1})]
    report = refine(candidates, [A("x")], limit=1)
    assert report.selected_ids == ("A",)
    assert report.swap is None and report.examined_swaps == 1
    assert report.objective == report.original_report.objective


def test_best_swap_ties_keep_unselected_input_order(refine):
    candidates, aspects = counterexample()
    candidates += [C("D", .6, dict(candidates[2].support))]
    report = refine(candidates, aspects, limit=2)
    assert report.selected_ids == ("C", "B")
    assert report.examined_swaps == 4


@pytest.mark.parametrize("limit", [0, 1, 3, 100])
def test_capacity_and_empty_neighborhood(refine, limit):
    candidates = [C("A", 1, {}), C("B", .5, {})]
    report = refine(candidates, [], limit=limit, relevance_weight=1)
    assert len(report.selected_ids) <= limit
    assert report.selected_ids == ("A", "B")[:limit]
    assert report.swap is None
    assert report.examined_swaps == len(report.selected_ids) * (2-len(report.selected_ids))


def test_zero_gain_pool_and_empty_input(refine):
    for candidates in ([], [C("zero", 0, {})]):
        report = refine(candidates, [A("x")], limit=5)
        assert report.selected_ids == () and report.swap is None
        assert report.objective == 0 and report.examined_swaps == 0
        assert report.uncovered_aspect_ids == ("x",)


def test_report_recomputes_partial_and_zero_weight_coverage(refine):
    candidates = [C("A", 0, {"x": .5, "ignored": 1}), C("B", 0, {"x": .25})]
    report = refine(candidates, [A("x"), A("ignored", 0), A("missing")], limit=1)
    assert report.partial_aspect_ids == ("x",)
    assert report.uncovered_aspect_ids == ("missing",)
    assert report.aspect_coverage == {"x": .5, "ignored": 1, "missing": 0}
    assert report.objective == .125


def test_snapshot_accepts_readonly_support_and_does_not_mutate_inputs(refine):
    candidates, aspects = counterexample()
    before = deepcopy((candidates, aspects))
    report = refine(candidates, aspects, limit=2)
    assert (candidates, aspects) == before
    candidates[0].support["1"] = 0
    assert report.original_report.aspect_coverage["1"] == 1
    readonly = [C(c.memory_id, c.relevance, MappingProxyType(dict(c.support))) for c in before[0]]
    assert refine(readonly, tuple(aspects), limit=2).selected_ids == ("C", "B")


@pytest.mark.parametrize("weight", [10**400, F(1, 10**400), 1e-300, 1e300])
def test_weight_scale_does_not_change_swap(refine, weight):
    candidates, aspects = counterexample()
    report = refine(candidates, [A(a.aspect_id, weight) for a in aspects], limit=2)
    assert report.selected_ids == ("C", "B")
    assert report.objective == pytest.approx(.8, abs=1e-15)


@pytest.mark.parametrize("dtype", ["float16", "float32"])
def test_foreign_scalar_weight_precision_survives_refinement(refine, dtype):
    np = pytest.importorskip("numpy")
    scalar = getattr(np, dtype)
    # Small positive weight must not vanish through division in source precision.
    small = scalar(2**(-24 if dtype == "float16" else -149))
    large = scalar(65504 if dtype == "float16" else 2**100)
    report = refine([C("A", 0, {"large": 1}), C("B", 0, {"small": 1})],
                    [A("small", small), A("large", large)], limit=2)
    assert report.selected_ids == ("A", "B")
    exact_small = F(*small.as_integer_ratio())
    exact_large = F(*large.as_integer_ratio())
    assert report.original_report.normalized_aspect_weights["small"] == float(exact_small / (exact_small+exact_large))
    assert report.swap is None


@pytest.mark.parametrize("candidates,aspects,kwargs,error", [
    ([], [A("x")], {"limit": True}, TypeError),
    ([], [A("x")], {"limit": .5}, TypeError),
    ([], [A("x")], {"limit": -1}, ValueError),
    ([], [A("x")], {"limit": 101}, ValueError),
    ([], [A("x")], {"relevance_weight": True}, TypeError),
    ([], [A("x")], {"relevance_weight": math.nan}, ValueError),
    ([], [A("x")], {"relevance_weight": math.inf}, ValueError),
    ([], [A("x")], {"relevance_weight": 1.1}, ValueError),
    ([], [], {}, ValueError),
    ([], [A("x", 0)], {}, ValueError),
    ([], [A("x", -1)], {}, ValueError),
    ([], [A("x", math.nan)], {}, ValueError),
    ([], [A("x"), A("x")], {}, ValueError),
    ([], [A(str(i)) for i in range(33)], {}, ValueError),
    ([C(str(i), 1, {}) for i in range(101)], [A("x")], {}, ValueError),
    ([C("A", 1, {}), C("A", 1, {})], [A("x")], {}, ValueError),
    ([C(" A", 1, {})], [A("x")], {}, ValueError),
    ([C("A", math.nan, {})], [A("x")], {}, ValueError),
    ([C("A", True, {})], [A("x")], {}, TypeError),
    ([C("A", 1.1, {})], [A("x")], {}, ValueError),
    ([C("A", 1, {"other": 1})], [A("x")], {}, ValueError),
    ([C("A", 1, {"x": -.1})], [A("x")], {}, ValueError),
    ([C("A", 1, {"x": math.inf})], [A("x")], {}, ValueError),
    ([C("A", 1, {"x": True})], [A("x")], {}, TypeError),
    ([C("A", 1, [])], [A("x")], {}, TypeError),
    ([object()], [A("x")], {}, TypeError),
    ([], [object()], {}, TypeError),
    ("invalid", [A("x")], {}, TypeError),
    ([], "invalid", {}, TypeError),
])
def test_validation_cannot_be_bypassed_even_at_zero_capacity(refine, candidates, aspects, kwargs, error):
    with pytest.raises(error):
        refine(candidates, aspects, **kwargs)
    with pytest.raises(error):
        refine(candidates, aspects, **(dict(kwargs) | {"limit": kwargs.get("limit", 0)}))


def exact_objective(candidates, aspects, ids, limit, lam):
    if not limit:
        return F(0)
    selected = [c for c in candidates if c.memory_id in ids]
    total = sum(F(a.weight) for a in aspects)
    relevance = sum(F(c.relevance) for c in selected) / limit
    coverage = sum(F(a.weight)/total * max((F(c.support.get(a.aspect_id, 0)) for c in selected), default=F(0)) for a in aspects)
    return lam*relevance + (1-lam)*coverage


def test_single_round_matches_independent_exact_original_neighborhood(refine):
    rng = random.Random(71007)
    for case in range(250):
        n = rng.randint(1, 8)
        limit = rng.randint(0, n+1)
        lam = rng.choice([F(0), F(1, 4), F(1, 2), F(3, 4), F(1)])
        aspects = [A(str(i), rng.randint(1, 5)) for i in range(rng.randint(1, 5))]
        candidates = [C(str(i), F(rng.randint(0, 8), 8),
                        {a.aspect_id: F(rng.randint(0, 4), 4) for a in aspects}) for i in range(n)]
        report = refine(candidates, aspects, limit=limit, relevance_weight=lam)
        initial = report.original_report.selected_ids
        original = exact_objective(candidates, aspects, initial, limit, lam)
        alternatives = [(original, initial)]
        for pos, _ in enumerate(initial):
            for c in candidates:
                if c.memory_id not in initial:
                    ids = initial[:pos] + (c.memory_id,) + initial[pos+1:]
                    alternatives.append((exact_objective(candidates, aspects, ids, limit, lam), ids))
        best = max(score for score, _ in alternatives)
        actual = exact_objective(candidates, aspects, report.selected_ids, limit, lam)
        assert float(actual) == pytest.approx(float(best), abs=2e-15), case
        assert actual >= original, case
        assert report.objective >= report.original_report.objective, case
        assert report.objective == pytest.approx(float(actual), abs=2e-15), case
        assert report.examined_swaps == len(initial)*(n-len(initial)), case
        assert len(initial) == len(report.selected_ids) <= limit, case
        assert len(set(initial)-set(report.selected_ids)) <= 1, case
        assert len(set(report.selected_ids)-set(initial)) <= 1, case
        if report.swap is not None:
            assert report.swap.objective_gain > 0
        else:
            assert report.selected_ids == initial


@pytest.mark.parametrize("limit,pairs", [(5, 475), (50, 2500)])
def test_candidate_aspect_and_pair_budgets(refine, limit, pairs):
    candidates = [C(str(i), 1, {}) for i in range(100)]
    report = refine(candidates, [A(str(i)) for i in range(32)], limit=limit)
    assert report.selected_ids == tuple(str(i) for i in range(limit))
    assert report.examined_swaps == pairs
    assert report.swap is None


def test_one_round_stops_even_when_another_swap_would_help(refine):
    rows = [(.25, "110000"), (1, "010101"), (1, "100101"),
            (.5, "000010"), (.5, "111101"), (.75, "100111"), (.75, "001111")]
    candidates = [C(str(i), r, {str(a): int(v) for a, v in enumerate(bits)})
                  for i, (r, bits) in enumerate(rows)]
    report = refine(candidates, [A(str(i)) for i in range(6)], limit=3)
    assert report.original_report.selected_ids == ("4", "5", "1")
    assert report.objective == pytest.approx(float(F(11, 12)), abs=1e-15)
    assert len(set(report.original_report.selected_ids)-set(report.selected_ids)) == 1
    # A second round could attain 23/24, but is outside the approved contract.
    assert report.objective < float(F(23, 24))
    assert report.examined_swaps == 12
