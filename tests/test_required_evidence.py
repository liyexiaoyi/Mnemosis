"""Required coverage is a constraint, independently checked against subsets."""
from copy import deepcopy
from fractions import Fraction as F
from itertools import combinations
import math
import random

import pytest
import mnemosis.evidence_selection as api


@pytest.fixture
def select():
    def call(*args, **kwargs):
        selector = getattr(api, "select_required_evidence", None)
        assert callable(selector), "required evidence selection is not implemented"
        return selector(*args, **kwargs)
    return call


def fixture():
    return ([api.EvidenceCandidate("A", 1, {"a": 1}),
             api.EvidenceCandidate("B", 1, {"a": 1}),
             api.EvidenceCandidate("C", F(3, 5), {"b": 1})],
            [api.QueryAspect("a"), api.QueryAspect("b")])


def test_required_role_cannot_be_compensated_by_relevance(select):
    cs, aspects = fixture()
    report = select(cs, aspects, required_aspects={"a": 1, "b": 1},
                    limit=2, relevance_weight=F(4, 5))
    assert report.baseline.selected_ids == ("A", "B")
    assert report.baseline.objective == pytest.approx(.9)
    assert report.selection.selected_ids == ("A", "C")
    assert report.selection.objective == pytest.approx(.84)
    assert report.status == "feasible"
    assert report.completeness == 1
    assert report.search_complete and report.optimality == "optimal"


def test_empty_requirements_preserve_old_selection_exactly(select):
    cs, aspects = fixture()
    old = api.select_evidence(cs, aspects, limit=2)
    new = select(cs, aspects, required_aspects={}, limit=2)
    assert new.selection == new.baseline == old
    assert new.status == "not_applicable"
    assert new.completeness is None
    assert new.optimality == "not_applicable"
    assert new.visited_nodes == 0


def test_zero_weight_required_role_is_still_mandatory(select):
    cs = [api.EvidenceCandidate("main", 0, {"a": 1}),
          api.EvidenceCandidate("needed", 0, {"b": 1})]
    r = select(cs, [api.QueryAspect("a"), api.QueryAspect("b", 0)],
               required_aspects={"b": 1}, relevance_weight=0, limit=2)
    assert r.selection.selected_ids == ("main", "needed")
    assert r.required_coverage == {"b": F(1)}
    assert r.completeness == 1


def test_full_pool_coverage_does_not_prove_capacity_feasibility(select):
    cs = [api.EvidenceCandidate(a, 0, {a: 1}) for a in "abc"]
    r = select(cs, [api.QueryAspect(a) for a in "abc"],
               required_aspects=dict.fromkeys("abc", 1), limit=2)
    assert r.pool_coverage == dict.fromkeys("abc", F(1))
    assert r.status == "infeasible" and r.search_complete
    assert r.selection is None and r.completeness is None


def test_budget_exhaustion_is_undetermined_not_infeasible(select):
    cs, aspects = fixture()
    r = select(cs, aspects, required_aspects={"a": 1, "b": 1},
               limit=2, relevance_weight=.8, search_budget=1)
    assert r.status == "undetermined"
    assert r.selection is None and not r.search_complete
    assert r.visited_nodes <= 1


def test_feasible_incumbent_is_kept_when_budget_exhausts(select):
    cs, aspects = fixture()
    r = select(cs, aspects, required_aspects={"a": 1, "b": 1},
               limit=2, relevance_weight=0, search_budget=0)
    assert r.status == "feasible"
    assert r.selection.selected_ids == ("A", "C")
    assert not r.search_complete and r.optimality == "not_proven"


@pytest.mark.parametrize("value,threshold,feasible", [
    (1 - F(1, 10**30), 1, False),
    (F(1, 10**400), F(1, 10**400), True),
    (F(1, 10**400), F(2, 10**400), False),
    (F(3, 4), F(1, 2), True),
])
def test_raw_support_and_threshold_precede_float_rounding(select, value, threshold, feasible):
    r = select([api.EvidenceCandidate("x", 0, {"a": value})],
               [api.QueryAspect("a")], required_aspects={"a": threshold}, limit=1)
    assert r.pool_coverage["a"] == value
    assert (r.status == "feasible") is feasible
    if feasible:
        assert r.completeness == 1
    else:
        assert r.status == "infeasible" and r.selection is None


def test_numpy_scalar_comparison_does_not_round_rational_threshold(select):
    np = pytest.importorskip("numpy")
    r = select([api.EvidenceCandidate("x", 0, {"a": np.float16(.5)})],
               [api.QueryAspect("a")],
               required_aspects={"a": F(1, 2) + F(1, 10**30)}, limit=1)
    assert r.status == "infeasible"


@pytest.mark.parametrize("mapping,state", [({}, "absent"),
    ({"a": 0}, "partial"), ({"a": 0, "b": 0}, "complete")])
def test_missing_annotations_are_separate_from_given_input_infeasibility(select, mapping, state):
    r = select([api.EvidenceCandidate("x", .9, mapping)],
               [api.QueryAspect("a"), api.QueryAspect("b")],
               required_aspects={"a": 1, "b": 1})
    assert r.status == "infeasible"
    assert r.support_state == state
    assert r.missing_support_pairs == tuple(("x", a) for a in "ab" if a not in mapping)


def test_false_support_annotations_still_pass_and_are_not_truth(select):
    r = select([api.EvidenceCandidate("generic-summary", 1, {"a": 1, "b": 1})],
               [api.QueryAspect("a"), api.QueryAspect("b")],
               required_aspects={"a": 1, "b": 1}, limit=1)
    assert r.status == "feasible"
    assert r.selection.selected_ids == ("generic-summary",)


def test_zero_capacity_proves_given_input_infeasibility(select):
    cs, aspects = fixture()
    r = select(cs, aspects, required_aspects={"a": 1}, limit=0, search_budget=0)
    assert r.status == "infeasible" and r.search_complete
    assert r.selection is None and r.visited_nodes == 0


@pytest.mark.parametrize("requirements,exception", [
    ({"a"}, TypeError), ({"unknown": 1}, ValueError), ({"a": 0}, ValueError),
    ({"a": -1}, ValueError), ({"a": 1.01}, ValueError), ({"a": True}, TypeError),
    ({"a": math.nan}, ValueError), ({"a": math.inf}, ValueError),
    ({"a": "1"}, TypeError),
])
def test_invalid_requirements_rejected_even_at_zero_capacity(select, requirements, exception):
    cs, aspects = fixture()
    with pytest.raises(exception):
        select(cs, aspects, required_aspects=requirements, limit=0)


def test_required_role_ids_default_to_full_support_threshold(select):
    cs, aspects = fixture()
    r = select(cs, aspects, required_aspects=("a", "b"), limit=2, relevance_weight=.8)
    explicit = select(cs, aspects, required_aspects={"a": 1, "b": 1},
                      limit=2, relevance_weight=.8)
    assert r == explicit


@pytest.mark.parametrize("requirements,exception", [("ab", TypeError),
    (["a", "a"], ValueError), (["unknown"], ValueError), ([True], TypeError)])
def test_invalid_role_sequences_rejected(select, requirements, exception):
    cs, aspects = fixture()
    with pytest.raises(exception):
        select(cs, aspects, required_aspects=requirements)


def test_two_replacements_and_zero_utility_witness_are_possible(select):
    cs = [api.EvidenceCandidate("A", 1, {"a": 1}),
          api.EvidenceCandidate("B", 1, {"a": 1}),
          api.EvidenceCandidate("C", 0, {"b": 1}),
          api.EvidenceCandidate("D", 0, {"c": 1})]
    r = select(cs, [api.QueryAspect(a) for a in "abc"],
               required_aspects={"b": 1, "c": 1}, limit=2, relevance_weight=1)
    assert r.baseline.selected_ids == ("A", "B")
    assert r.selection.selected_ids == ("C", "D")
    assert r.selection.objective == 0 and r.completeness == 1


@pytest.mark.parametrize("budget,exception", [(True, TypeError), (1.5, TypeError),
    (-1, ValueError), (100001, ValueError)])
def test_invalid_search_budget_rejected_with_empty_requirements(select, budget, exception):
    with pytest.raises(exception):
        select([], [], required_aspects={}, relevance_weight=1, search_budget=budget)


def test_original_validation_cannot_be_bypassed(select):
    with pytest.raises(ValueError):
        select([api.EvidenceCandidate("x", 1, {"a": 2})], [api.QueryAspect("a")],
               required_aspects={"a": 1}, limit=0)


def test_input_order_ties_and_inputs_remain_stable(select):
    cs, aspects = fixture()
    required = {"a": 1, "b": 1}
    before = deepcopy((cs, aspects, required))
    reports = [select(cs, aspects, required_aspects=required, limit=2) for _ in range(2)]
    assert reports[0] == reports[1]
    assert reports[0].selection.selected_ids == ("A", "C")
    assert (cs, aspects, required) == before


def test_bounded_search_matches_independent_small_subset_oracle(select):
    rng = random.Random(71007)
    for case in range(60):
        n, m, k = rng.randrange(1, 8), rng.randrange(1, 5), rng.randrange(0, 5)
        ids = [f"a{a}" for a in range(m)]
        raw_weights = [rng.randrange(1, 5) for _ in ids]
        aspects = [api.QueryAspect(a, w) for a, w in zip(ids, raw_weights)]
        cs = [api.EvidenceCandidate(str(i), F(rng.randrange(5), 4),
              {a: F(rng.randrange(5), 4) for a in ids}) for i in range(n)]
        required = {a: F(rng.randrange(1, 5), 4) for a in ids if rng.randrange(2)}
        if not required:
            required[ids[0]] = F(1)
        lam = F(rng.randrange(5), 4)
        feasible = []
        for size in range(min(n, k) + 1):
            for subset in combinations(range(n), size):
                coverage = {a: max((cs[i].support[a] for i in subset), default=F(0)) for a in ids}
                if all(coverage[a] >= t for a, t in required.items()):
                    utility = lam * sum((cs[i].relevance for i in subset), F(0)) / k
                    utility += (1-lam) * sum((F(w, sum(raw_weights))*coverage[a]
                                            for a, w in zip(ids, raw_weights)), F(0))
                    feasible.append(utility)
        r = select(cs, aspects, required_aspects=required, limit=k,
                   relevance_weight=lam, search_budget=10000)
        assert r.search_complete, case
        assert (r.status == "feasible") == bool(feasible), case
        if feasible:
            assert r.selection.objective == pytest.approx(float(max(feasible)), abs=1e-14), case
            assert len(r.selection.selected_ids) <= k
            assert all(r.required_coverage[a] >= t for a, t in required.items())
