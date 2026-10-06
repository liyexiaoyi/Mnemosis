"""Catch wrong fusion order, changed weights, missing validation and false coverage."""
from copy import deepcopy
from fractions import Fraction as F
import importlib
import math
import random
from types import MappingProxyType

import pytest
from mnemosis.evidence_selection import QueryAspect as A
from mnemosis.ranked_evidence import RankedChannel as R, select_ranked_evidence


@pytest.fixture
def refine():
    try:
        return importlib.import_module("mnemosis.ranked_evidence_refinement").refine_ranked_evidence
    except ModuleNotFoundError as exc:
        if exc.name != "mnemosis.ranked_evidence_refinement":
            raise
        def missing(*args, **kwargs):
            pytest.fail("approved ranked evidence refinement is not implemented")
        return missing


def trap():
    return ([R("L", ["A", "B", "C"]), R("D", ["A", "C", "B"])],
            [A(str(i)) for i in range(1, 7)],
            {"A": {str(i): 1 for i in (1, 2, 3, 4)},
             "B": {str(i): 1 for i in (1, 2, 5)},
             "C": {str(i): 1 for i in (3, 4, 6)}})


def test_fusion_and_best_swap_keep_original_report_separate(refine):
    channels, aspects, support = trap()
    report = refine(channels, aspects, support=support, limit=2, relevance_weight=0)
    assert report.ranked_report.candidate_ids == ("A", "B", "C")
    assert report.ranked_report.selection.selected_ids == ("A", "B")
    assert report.refinement.selected_ids == ("C", "B")
    assert report.refinement.original_report == report.ranked_report.selection
    assert report.ranked_report == select_ranked_evidence(channels, aspects, support=support, limit=2, relevance_weight=0)
    assert report.ranked_report.relevance_by_id["A"] == 1
    assert report.ranked_report.relevance_by_id["B"] == pytest.approx(float(F(7625, 7812)), abs=1e-15)
    assert report.refinement.objective == report.refinement.coverage_component == 1
    assert report.refinement.swap.objective_gain == pytest.approx(float(F(1, 6)), abs=1e-15)
    assert report.refinement.examined_swaps == 2
    assert tuple(s.memory_id for s in report.ranked_report.selection.steps) == ("A", "B")


def test_complementary_fusion_is_unchanged_when_no_swap_helps(refine):
    report = refine([R("L", ["A", "B", "C"]), R("D", ["A", "C", "B"])],
                    [A("X", .6), A("Y", .4)],
                    support={"A": {"X": 1}, "B": {"X": 1}, "C": {"Y": 1}}, limit=2)
    assert report.refinement.selected_ids == ("A", "C")
    assert report.refinement.swap is None
    assert report.refinement.objective == pytest.approx(float(F(31061, 31248)), abs=1e-15)


def test_missing_support_requires_explicit_relevance_at_all_capacities(refine):
    for support in (None, {}, {"A": {}}):
        for limit in (0, 2):
            with pytest.raises(ValueError):
                refine([R("L", ["A", "B"])], [A("x")], support=support, limit=limit)
            report = refine([R("L", ["A", "B"])], [A("x")], support=support, limit=limit, relevance_weight=1)
            assert report.ranked_report.support_state == "not_supplied"
            assert report.refinement.selected_ids == ("A", "B")[:limit]
            assert report.refinement.swap is None
            assert report.refinement.uncovered_aspect_ids == ("x",)


def test_explicit_zero_support_is_not_treated_as_absent(refine):
    report = refine([R("L", ["A"])], [A("x")], support={"A": {"x": 0}})
    assert report.ranked_report.support_state == "supplied"
    assert report.ranked_report.supplied_support_pairs == (("A", "x"),)
    assert report.refinement.uncovered_aspect_ids == ("x",)
    assert report.refinement.objective == .1


def test_empty_and_disabled_channels_retain_status_and_denominator(refine):
    report = refine([R("L", ["A"]), R("empty", []), R("disabled", [], 0, "failed")],
                    [], relevance_weight=1)
    assert report.ranked_report.relevance_by_id == {"A": .5}
    assert report.ranked_report.channels[2].status == "failed"
    assert report.ranked_report.channels[2].enabled is False
    assert report.refinement.objective == .1
    empty = refine([R("L", [])], [], relevance_weight=1)
    assert empty.refinement.selected_ids == () and empty.refinement.examined_swaps == 0


def test_coarse_support_can_still_miss_necessary_time_chain(refine):
    # A broad summary claims both aspects, but B and C are the actual events.
    report = refine([R("L", ["A", "B", "C"])], [A("arrival"), A("departure")],
                    support={"A": {"arrival": 1, "departure": 1},
                             "B": {"arrival": 1}, "C": {"departure": 1}}, limit=2)
    assert report.refinement.selected_ids == ("A", "B")
    assert report.refinement.coverage_component == 1
    assert not {"B", "C"}.issubset(report.refinement.selected_ids)
    assert report.refinement.swap is None


def test_inputs_and_other_reports_share_no_mutable_containers(refine):
    channels, aspects, support = trap()
    before = deepcopy((channels, aspects, support))
    report = refine(channels, aspects, support=support, limit=2, relevance_weight=0)
    assert (channels, aspects, support) == before
    support["A"]["1"] = 0
    channels[0].memory_ids.clear()
    assert report.ranked_report.candidate_ids == ("A", "B", "C")
    assert report.refinement.original_report.aspect_coverage["1"] == 1
    report.ranked_report.selection.aspect_coverage["1"] = 0
    assert report.refinement.original_report.aspect_coverage["1"] == 1
    immutable = MappingProxyType({k: MappingProxyType(v) for k, v in before[2].items()})
    assert refine(tuple(before[0]), tuple(before[1]), support=immutable, limit=2, relevance_weight=0).refinement.selected_ids == ("C", "B")


@pytest.mark.parametrize("scale", [10**400, F(1, 10**400), 1e300])
def test_weight_scaling_is_preserved_in_both_models(refine, scale):
    channels, aspects, support = trap()
    scaled = [R(c.channel_id, c.memory_ids, scale) for c in channels]
    report = refine(scaled, [A(a.aspect_id, scale) for a in aspects], support=support, limit=2, relevance_weight=0)
    assert report.refinement.selected_ids == ("C", "B")
    assert report.refinement.objective == 1
    assert report.ranked_report.relevance_by_id["B"] == pytest.approx(float(F(7625, 7812)), abs=1e-15)


@pytest.mark.parametrize("dtype", ["float16", "float32"])
def test_foreign_scalar_channel_and_aspect_precision(refine, dtype):
    np = pytest.importorskip("numpy")
    scalar = getattr(np, dtype)
    small = scalar(2**(-24 if dtype == "float16" else -149))
    large = scalar(65504 if dtype == "float16" else 2**100)
    report = refine([R("small", ["B"], small), R("large", ["A"], large)],
                    [A("small", small), A("large", large)],
                    support={"A": {"large": 1}, "B": {"small": 1}}, limit=2, relevance_weight=0)
    assert report.refinement.selected_ids == ("A", "B")
    exact = float(F(*small.as_integer_ratio()) / (F(*small.as_integer_ratio())+F(*large.as_integer_ratio())))
    assert report.ranked_report.channels[0].normalized_weight == exact
    assert report.refinement.original_report.normalized_aspect_weights["small"] == exact
    assert report.refinement.original_report == report.ranked_report.selection


def test_underflowed_positive_channel_candidates_are_not_dropped(refine):
    report = refine([R("large", ["A"], 1e308), R("tiny", ["B"], 1e-308)],
                    [A("x"), A("y")], support={"A": {"x": 1}, "B": {"y": 1}},
                    limit=2, relevance_weight=0)
    assert report.ranked_report.underflow_channel_ids == ("tiny",)
    assert report.ranked_report.relevance_by_id["B"] == 0
    assert report.refinement.selected_ids == ("A", "B")
    assert report.refinement.coverage_component == 1


@pytest.mark.parametrize("channels,aspects,support,options,error", [
    ([], [], None, {"relevance_weight": 1}, ValueError),
    ("bad", [], None, {"relevance_weight": 1}, TypeError),
    ([object()], [], None, {"relevance_weight": 1}, TypeError),
    ([R(str(i), []) for i in range(9)], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", ["A", "A"])], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", ["A"], -1)], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", ["A"], math.nan)], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", [], status="failed")], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", [], status="bad")], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", ["A"]), R("disabled", ["B", "B"], 0)], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", [str(i) for i in range(101)])], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", [str(i) for i in range(100)]), R("y", ["extra"])], [], None, {"relevance_weight": 1}, ValueError),
    ([R("x", ["A"])], [A(str(i)) for i in range(33)], None, {"relevance_weight": 1}, ValueError),
    ([R("x", ["A"])], [A("a", -1)], {"A": {"a": 1}}, {}, ValueError),
    ([R("x", ["A"])], [A("a"), A("a")], {"A": {"a": 1}}, {}, ValueError),
    ([R("x", ["A"])], "bad", None, {"relevance_weight": 1}, TypeError),
    ([R("x", ["A"])], [A("a")], [], {}, TypeError),
    ([R("x", ["A"])], [A("a")], {"B": {"a": 1}}, {}, ValueError),
    ([R("x", ["A"])], [A("a")], {"A": []}, {}, TypeError),
    ([R("x", ["A"])], [A("a")], {"A": {"b": 1}}, {}, ValueError),
    ([R("x", ["A"])], [A("a")], {"A": {"a": True}}, {}, TypeError),
    ([R("x", ["A"])], [A("a")], {"A": {"a": math.inf}}, {}, ValueError),
    ([R("x", ["A"])], [A("a")], {"A": {"a": -.1}}, {}, ValueError),
    ([R("x", ["A"])], [A("a")], {str(i): {} for i in range(101)}, {}, ValueError),
    ([R("x", ["A"])], [A("a")], {"A": {str(i): 1 for i in range(33)}}, {}, ValueError),
    ([R("x", ["A"])], [], None, {"relevance_weight": True}, TypeError),
    ([R("x", ["A"])], [], None, {"relevance_weight": 1, "limit": True}, TypeError),
    ([R("x", ["A"])], [], None, {"relevance_weight": 1, "limit": -1}, ValueError),
    ([R("x", ["A"])], [], None, {"relevance_weight": 1, "limit": 101}, ValueError),
])
def test_invalid_inputs_still_fail_at_zero_capacity(refine, channels, aspects, support, options, error):
    with pytest.raises(error):
        refine(channels, aspects, support=support, **(dict(options) | {"limit": options.get("limit", 0)}))


@pytest.mark.parametrize("limit,pairs", [(0, 0), (5, 475), (50, 2500), (100, 0)])
def test_union_aspect_and_swap_budgets_are_retained(refine, limit, pairs):
    ids = [str(i) for i in range(100)]
    channels = [R(str(j), ids[j:]+ids[:j]) for j in range(8)]
    aspects = [A(str(j)) for j in range(32)]
    report = refine(channels, aspects, support={i: {"0": 0} for i in ids}, limit=limit)
    assert len(report.ranked_report.candidate_ids) == 100
    assert len(report.refinement.selected_ids) == limit
    assert report.refinement.examined_swaps == pairs


def test_independent_rank_math_and_original_neighborhood_enumeration(refine):
    rng = random.Random(71010)
    for case in range(150):
        ids = [str(i) for i in range(rng.randint(1, 8))]
        channels = []
        for j in range(rng.randint(1, 4)):
            order = rng.sample(ids, len(ids))
            channels.append(R(str(j), order, rng.randint(1, 5)))
        aspects = [A(str(i), rng.randint(1, 5)) for i in range(rng.randint(1, 4))]
        support = {i: {a.aspect_id: F(rng.randint(0, 4), 4) for a in aspects} for i in ids}
        limit = rng.randint(0, len(ids)+1)
        lam = rng.choice([F(0), F(1, 4), F(1, 2), F(1)])
        report = refine(channels, aspects, support=support, limit=limit, relevance_weight=lam)
        total = sum(F(c.weight) for c in channels)
        relevance = {i: sum(F(c.weight)/total * F(61, 61+c.memory_ids.index(i)) for c in channels) for i in ids}
        for i in ids:
            assert report.ranked_report.relevance_by_id[i] == pytest.approx(float(relevance[i]), abs=2e-15), case
        def exact(selected):
            if not limit:
                return F(0)
            return lam*sum(relevance[i] for i in selected)/limit + (1-lam)*sum(F(a.weight)/sum(F(b.weight) for b in aspects)*max((support[i][a.aspect_id] for i in selected), default=F(0)) for a in aspects)
        initial = report.ranked_report.selection.selected_ids
        original = exact(initial)
        alternatives = [original]
        for pos in range(len(initial)):
            for i in report.ranked_report.candidate_ids:
                if i not in initial:
                    alternatives.append(exact(initial[:pos]+(i,)+initial[pos+1:]))
        actual = exact(report.refinement.selected_ids)
        assert float(actual) == pytest.approx(float(max(alternatives)), abs=3e-15), case
        assert actual >= original, case
        assert report.refinement.objective == pytest.approx(float(actual), abs=3e-15), case
        assert report.refinement.original_report == report.ranked_report.selection, case
        assert len(set(initial)-set(report.refinement.selected_ids)) <= 1, case
