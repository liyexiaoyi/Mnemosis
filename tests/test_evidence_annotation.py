"""Catch false support, lost unknowns and quotations bound to wrong text."""
import importlib

import pytest

from mnemosis.ranked_evidence_refinement import SupportSpan


def api():
    return importlib.import_module("mnemosis.evidence_annotation")


def decision(memory="m0", aspect="a0", verdict="supported", quote="大阪"):
    return dict(memory_id=memory, aspect_id=aspect, verdict=verdict, quote=quote)


def test_quote_uses_codepoints_and_unknown_is_absent():
    a = api()
    result = a.parse_support_batch({"decisions": [decision(), decision("m1", verdict="unknown", quote=None)]},
        aspects=(a.EvidenceAspect("a0", "目的地"),), source_texts={"m0": "🙂去大阪", "m1": "未说明"})
    assert result.support == {"m0": {"a0": 1}}
    assert result.spans["m0"]["a0"] == SupportSpan(2, 4, "大阪")
    assert result.unknown_pairs == (("m1", "a0"),)


def test_explicit_negative_and_missing_remain_different():
    a = api()
    result = a.parse_support_batch({"decisions": [decision(verdict="not_supported", quote=None)]},
        aspects=(a.EvidenceAspect("a0", "目的地"),), source_texts={"m0": "未知", "m1": "未知"})
    assert result.support == {"m0": {"a0": 0}}
    assert result.spans == {}
    assert result.unknown_pairs == (("m1", "a0"),)


@pytest.mark.parametrize("text,quote", [("大阪大阪", "大阪"), ("aaa", "aa"),
    ("Osaka", "大阪"), ("e\u0301", "é"), ("大阪", "")])
def test_unbound_or_ambiguous_quote_rejects_whole_batch(text, quote):
    a = api()
    with pytest.raises(ValueError):
        a.parse_support_batch({"decisions": [decision(quote=quote)]},
            aspects=(a.EvidenceAspect("a0", "場所"),), source_texts={"m0": text})


@pytest.mark.parametrize("rows", [
    [decision("other")], [decision(aspect="other")], [decision(), decision()],
    [decision(verdict="maybe")], [decision(verdict="unknown")],
    [decision(verdict="not_supported")], [{**decision(), "weight": 1}],
    [{**decision(), "memory_id": True}], [decision(quote=12)],
])
def test_invalid_or_duplicate_decision_cannot_override_valid_support(rows):
    a = api()
    with pytest.raises((ValueError, TypeError)):
        a.parse_support_batch({"decisions": rows}, aspects=(a.EvidenceAspect("a0", "場所"),),
                              source_texts={"m0": "大阪"})


def test_64_decisions_allowed_and_65_rejected():
    a = api()
    aspects = tuple(a.EvidenceAspect(f"a{i}", str(i)) for i in range(8))
    texts = {f"m{i}": "大阪" for i in range(8)}
    rows = [decision(m, aspect=role.aspect_id, verdict="not_supported", quote=None)
            for m in texts for role in aspects]
    result = a.parse_support_batch({"decisions": rows}, aspects=aspects, source_texts=texts)
    assert sum(map(len, result.support.values())) == 64
    with pytest.raises(ValueError):
        a.parse_support_batch({"decisions": rows + [decision()]}, aspects=aspects, source_texts=texts)


def test_plan_assigns_ids_and_does_not_accept_model_weights():
    a = api()
    p = a.parse_question_plan({"scope": "finite", "aspects": ["  地点  ", "日期"]})
    assert [(x.aspect_id, x.description) for x in p.aspects] == [("a0", "地点"), ("a1", "日期")]
    assert a.parse_question_plan({"scope": "finite", "aspects": []}).aspects == ()
    assert len(a.parse_question_plan({"scope": "finite", "aspects": ["x" * 512] * 8}).aspects) == 8


@pytest.mark.parametrize("payload", [None, {"scope": "maybe", "aspects": []},
    {"scope": "finite", "aspects": [" "]}, {"scope": "finite", "aspects": [1]},
    {"scope": "finite", "aspects": ["x" * 513]}, {"scope": "finite", "aspects": ["x"] * 9},
    {"scope": "finite", "aspects": ["x"], "weight": 1}, {"scope": "finite", "aspects": "x"}])
def test_malformed_plan_rejected(payload):
    with pytest.raises((ValueError, TypeError)):
        api().parse_question_plan(payload)


def test_literal_quote_does_not_claim_entailment():
    a = api()
    result = a.parse_support_batch({"decisions": [decision(quote="未去大阪")]},
        aspects=(a.EvidenceAspect("a0", "去了大阪"),), source_texts={"m0": "未去大阪"})
    # Deliberately wrong semantic annotation passes literal grounding only.
    assert result.support == {"m0": {"a0": 1}}
