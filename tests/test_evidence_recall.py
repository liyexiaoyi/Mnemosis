"""Catch false completion, rank/score confusion and late input validation."""
import importlib
from datetime import datetime, timezone
from fractions import Fraction

import pytest

from evidence_fixtures import FixedAnnotator, FrozenEngine, results

NOW = datetime(2026, 10, 7, 12, tzinfo=timezone.utc)


def api():
    return importlib.import_module("mnemosis.evidence_recall")


def test_combination_finds_missing_date_and_keeps_original_score():
    engine, provider = FrozenEngine(), FixedAnnotator()
    report = api().recall_evidence(engine, "Where and when was Mina's trip?", annotator=provider,
                                  now=NOW, top_k=2, lexical_policy="inflection")
    assert report.status == "feasible" and report.annotation_status == "complete"
    assert [r.item.id for r in report.results] == ["A", "C"]
    assert [r.item.id for r in report.baseline] == ["A", "B"]
    assert [r.score for r in report.results] == [100, 98]
    assert all(not r.confident for r in report.results)
    assert report.relevance_by_id == {"A": 1, "B": 61 / 62, "C": 61 / 63}
    assert report.selector.completeness == Fraction(1)
    assert report.to_dict()["selector"]["completeness"] == "1/1"
    assert "model_replies" not in report.to_dict()
    assert len(engine.calls) == 1
    kwargs = engine.calls[0][1]
    assert kwargs["top_k"] == 100 and kwargs["read_only"] is True and kwargs["now"] == NOW
    assert kwargs["lexical_policy"] == "inflection"
    assert provider.calls[0][2] == provider.calls[1][2]


@pytest.mark.parametrize("kwargs", [
    {"top_k": True}, {"candidate_limit": False}, {"top_k": 101}, {"candidate_limit": 0},
    {"top_k": 3, "candidate_limit": 2}, {"search_budget": -1}, {"search_budget": True},
    {"relevance_weight": float("nan")}, {"relevance_weight": True}, {"kind": "episodic"},
    {"lexical_policy": "bad"}, {"temporal_policy": "bad"}, {"candidate_policy": "bad"},
    {"rerank_policy": "semantic_reserve"}, {"now": datetime(2026, 10, 7)},
    {"exclude_ids": ["A"]}, {"exclude_ids": {""}}, {"context": 12},
    {"annotator": None}, {"candidate_policy": "quota"},
])
def test_invalid_config_never_retrieves_or_calls_model(kwargs):
    engine, provider = FrozenEngine(), FixedAnnotator()
    args = {"annotator": provider, **kwargs}
    with pytest.raises((ValueError, TypeError)):
        api().recall_evidence(engine, "trip?", **args)
    assert engine.calls == [] and provider.calls == []


@pytest.mark.parametrize("query", ["", "  ", "x" * 4097, None], ids=["empty", "blank", "long", "not_string"])
def test_invalid_question_rejected_before_retrieval(query):
    engine = FrozenEngine()
    with pytest.raises((ValueError, TypeError)):
        api().recall_evidence(engine, query, annotator=FixedAnnotator())
    assert engine.calls == []


@pytest.mark.parametrize("limit,budget,want", [(1, 10000, "infeasible"), (2, 0, "undetermined")])
def test_no_witness_returns_empty_selection_not_baseline(limit, budget, want):
    r = api().select_from_snapshot("trip?", results(), annotator=FixedAnnotator(), top_k=limit,
                                  relevance_weight=.99, search_budget=budget)
    assert r.status == want and r.results == () and r.selector.selection is None
    assert r.baseline


@pytest.mark.parametrize("provider,status", [
    (FixedAnnotator(plan_error="timeout"), "annotation_failed"),
    (FixedAnnotator(scope="bad"), "annotation_failed"),
    (FixedAnnotator(rows=[]), "annotation_failed"),
    (FixedAnnotator(batch_error="timeout"), "annotation_failed"),
    (FixedAnnotator(scope="open_set"), "not_applicable"),
    (FixedAnnotator(scope="unsupported"), "not_applicable"),
    (FixedAnnotator(roles=()), "not_applicable"),
])
def test_failed_annotation_and_not_applicable_are_not_feasible(provider, status):
    r = api().select_from_snapshot("trip?", results(), annotator=provider, top_k=2,
                                  relevance_weight=.5, search_budget=10000)
    assert r.status == status and r.selector is None
    assert bool(r.results) == (status == "not_applicable")


@pytest.mark.parametrize("query", ["List all trips", "Every trip?", "所有旅行", "哪些地点？"])
def test_open_set_guard_does_not_claim_complete(query):
    provider = FixedAnnotator()
    r = api().recall_evidence(FrozenEngine(), query, annotator=provider)
    assert r.status == "not_applicable" and provider.calls == []


def test_small_does_not_match_all_word_guard():
    r = api().recall_evidence(FrozenEngine(), "Where and when was the small trip?", annotator=FixedAnnotator())
    assert r.status == "feasible"


def test_empty_pool_never_calls_model():
    provider = FixedAnnotator()
    r = api().recall_evidence(FrozenEngine([]), "trip?", annotator=provider)
    assert r.status == "not_applicable" and r.reason == "empty_candidate_pool"
    assert r.results == () and provider.calls == []


def test_partial_support_can_be_feasible_but_not_complete_annotation():
    rows = [dict(memory_id=m, aspect_id=a, verdict="supported", quote=q)
            for m, a, q in (("A", "a0", "Osaka"), ("C", "a1", "October"))]
    r = api().recall_evidence(FrozenEngine(), "trip?", annotator=FixedAnnotator(rows=rows), top_k=2)
    assert r.status == "feasible" and r.annotation_status == "partial"
    assert r.selector.missing_support_pairs


def test_all_valid_negatives_are_infeasible_and_distinct_from_missing():
    rows = [dict(memory_id=m, aspect_id=a, verdict="not_supported", quote=None)
            for m in ("A", "B", "C") for a in ("a0", "a1")]
    r = api().recall_evidence(FrozenEngine(), "trip?", annotator=FixedAnnotator(rows=rows))
    assert r.status == "infeasible" and r.annotation_status == "complete" and r.results == ()


def test_snapshot_survives_provider_mutating_original_objects():
    engine = FrozenEngine()
    provider = FixedAnnotator(hook=lambda: setattr(engine.rows[0].item, "content", "modified"))
    r = api().recall_evidence(engine, "trip?", annotator=provider, top_k=2)
    assert r.results[0].item.content == "Mina went to Osaka."
