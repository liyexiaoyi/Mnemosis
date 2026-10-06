"""Catch misbound quotes, invalid offsets, bypassed checks and altered scoring."""
from copy import deepcopy
from dataclasses import asdict
from fractions import Fraction
import importlib
from types import MappingProxyType, SimpleNamespace

import pytest
from mnemosis.evidence_selection import QueryAspect as A
from mnemosis.ranked_evidence import RankedChannel as R


@pytest.fixture
def api():
    module = importlib.import_module("mnemosis.ranked_evidence_refinement")
    if not hasattr(module, "SupportSpan"):
        def missing(*args, **kwargs):
            pytest.fail("approved optional support-span validation is not implemented")
        return SimpleNamespace(SupportSpan=missing, refine_ranked_evidence=missing,
                               select_ranked_evidence=module.select_ranked_evidence,
                               refine_evidence=module.refine_evidence)
    return module


def inputs():
    return ([R("L", ["A", "B"])], [A("x")],
            {"A": {"x": 1}, "B": {"x": 0}},
            {"A": "李明😀到了北京。", "B": "other"})


def call(api, *, limit=1, **changes):
    channels, aspects, support, texts = inputs()
    args = {"support": support, "source_texts": texts,
            "support_spans": {"A": {"x": api.SupportSpan(3, 8, "到了北京。")}}, "limit": limit}
    channels = changes.pop("channels", channels)
    aspects = changes.pop("aspects", aspects)
    args.update(changes)
    return api.refine_ranked_evidence(channels, aspects, **args)


def test_valid_unicode_codepoint_span_keeps_scores_and_report_shape(api):
    channels, aspects, support, _ = inputs()
    baseline = api.refine_ranked_evidence(channels, aspects, support=support, limit=1)
    actual = call(api)
    assert asdict(actual) == asdict(baseline)
    assert actual.refinement.selected_ids == ("A",)
    assert actual.refinement.objective == 1
    assert set(asdict(actual)) == {"ranked_report", "refinement"}


def test_both_none_preserve_legacy_and_one_missing_argument_errors(api):
    channels, aspects, support, texts = inputs()
    baseline = api.refine_ranked_evidence(channels, aspects, support=support, limit=1)
    assert api.refine_ranked_evidence(channels, aspects, support=support, limit=1,
                                     source_texts=None, support_spans=None) == baseline
    for options in ({"source_texts": texts}, {"support_spans": {}},
                    {"source_texts": {}, "support_spans": None}):
        with pytest.raises(ValueError):
            api.refine_ranked_evidence(channels, aspects, support=support, limit=0, **options)


@pytest.mark.parametrize("start,end,quote,error", [
    (-1, 8, "到了北京。", ValueError), (3, 3, "", ValueError),
    (8, 3, "到了北京。", ValueError), (3, 99, "到了北京。", ValueError),
    (True, 8, "到了北京。", TypeError), (3, False, "到了北京。", TypeError),
    (3., 8, "到了北京。", TypeError), (3, 8., "到了北京。", TypeError),
    ("3", 8, "到了北京。", TypeError), (3, "8", "到了北京。", TypeError),
    (3, 8, "", ValueError), (3, 8, None, TypeError),
    (3, 8, b"wrong", TypeError), (3, 8, "到了上海。", ValueError),
    (4, 9, "到了北京。", ValueError), (3, 8, "到了北京。 ", ValueError),
])
def test_invalid_spans_fail_even_at_zero_capacity(api, start, end, quote, error):
    with pytest.raises(error):
        call(api, limit=0, support_spans={"A": {"x": api.SupportSpan(start, end, quote)}})


@pytest.mark.parametrize("changes,error", [
    ({"source_texts": []}, TypeError), ({"support_spans": []}, TypeError),
    ({"source_texts": {"A": 12}}, TypeError),
    ({"source_texts": {"A": "李明😀到了北京。", "C": "other"}}, ValueError),
    ({"source_texts": {" A": "李明😀到了北京。"}}, ValueError),
    ({"source_texts": {}}, ValueError), ({"support_spans": {}}, ValueError),
    ({"support_spans": {"A": []}}, TypeError),
    ({"support_spans": {"A": {"x": (3, 8, "到了北京。")}}}, TypeError),
    ({"support_spans": {"C": {"x": None}}}, ValueError),
    ({"support_spans": {"A": {"other": None}}}, ValueError),
    ({"source_texts": {str(i): "x" for i in range(101)}}, ValueError),
    ({"support_spans": {str(i): {} for i in range(101)}}, ValueError),
    ({"support_spans": {"A": {str(i): None for i in range(33)}}}, ValueError),
])
def test_bad_grounding_maps_are_not_ignored(api, changes, error):
    with pytest.raises(error):
        call(api, limit=0, **changes)


def test_extra_span_must_refer_to_supplied_pair_and_zero_span_is_validated(api):
    positive = api.SupportSpan(3, 8, "到了北京。")
    report = call(api, support_spans={"A": {"x": positive}, "B": {"x": api.SupportSpan(0, 5, "other")}})
    assert report == call(api)
    with pytest.raises(ValueError):
        call(api, limit=0, support_spans={"A": {"x": positive}, "B": {"x": api.SupportSpan(0, 5, "wrong")}})
    with pytest.raises(ValueError):
        call(api, support={"A": {"x": 1}, "B": {}},
             support_spans={"A": {"x": positive}, "B": {"x": api.SupportSpan(0, 5, "other")}})


def test_zero_or_absent_support_needs_no_witness_but_legacy_rules_remain(api):
    for support in (None, {}, {"A": {"x": 0}}):
        report = call(api, support=support, source_texts={}, support_spans={}, relevance_weight=1)
        assert report.refinement.selected_ids == ("A",)
    with pytest.raises(ValueError):
        call(api, support=None, source_texts={}, support_spans={})
    with pytest.raises(ValueError):
        call(api, support={"A": {"x": Fraction(1, 10**400)}}, support_spans={})
    tiny = call(api, support={"A": {"x": Fraction(1, 10**400)}}, relevance_weight=0)
    assert tiny.refinement.selected_ids == ()  # score conversion still underflows as before


def test_no_case_whitespace_or_unicode_normalization_is_performed(api):
    cases = (("Trip", "trip", 4), ("e"+chr(0x301), "é", 2),
             (chr(13)+chr(10), chr(10), 2))
    for text, quote, end in cases:
        with pytest.raises(ValueError):
            call(api, source_texts={"A": text}, support_spans={"A": {"x": api.SupportSpan(0, end, quote)}})


def test_complete_crlf_quote_matches_without_changing_scoring(api):
    text = chr(13)+chr(10)
    report = call(api, source_texts={"A": text},
                  support_spans={"A": {"x": api.SupportSpan(0, 2, text)}})
    assert report.refinement.objective == 1


def test_validation_stops_pipeline_before_ranking_or_selection(api, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("ranking/selection ran before invalid quote was rejected")
    monkeypatch.setattr(api, "select_ranked_evidence", forbidden)
    monkeypatch.setattr(api, "refine_evidence", forbidden)
    with pytest.raises(ValueError, match="A.*x"):
        call(api, support_spans={"A": {"x": api.SupportSpan(3, 8, "wrong")}})


def test_matching_generic_quote_does_not_prove_semantic_support(api):
    channels = [R("L", ["A", "B", "C"])]
    aspects = [A("arrival"), A("departure")]
    texts = {"A": "Mina discussed a trip.", "B": "Mina arrived.", "C": "Mina departed."}
    support = {"A": {"arrival": 1, "departure": 1}, "B": {"arrival": 1}, "C": {"departure": 1}}
    spans = {i: {a: api.SupportSpan(0, len(texts[i]), texts[i]) for a in values} for i, values in support.items()}
    report = api.refine_ranked_evidence(channels, aspects, support=support, limit=2,
                                      source_texts=texts, support_spans=spans)
    assert report.refinement.selected_ids == ("A", "B")
    assert report.refinement.coverage_component == 1
    assert not {"B", "C"}.issubset(report.refinement.selected_ids)
    spans["A"]["arrival"] = api.SupportSpan(0, len(texts["B"]), texts["B"])
    with pytest.raises(ValueError):
        api.refine_ranked_evidence(channels, aspects, support=support, limit=2,
                                  source_texts=texts, support_spans=spans)


def test_source_and_span_snapshots_do_not_modify_inputs(api):
    channels, aspects, support, texts = inputs()
    spans = {"A": {"x": api.SupportSpan(3, 8, "到了北京。")}}
    before = deepcopy((channels, aspects, support, texts, spans))
    report = api.refine_ranked_evidence(channels, aspects, support=support, limit=1,
                                      source_texts=MappingProxyType(texts),
                                      support_spans=MappingProxyType({"A": MappingProxyType(spans["A"])}))
    assert (channels, aspects, support, texts, spans) == before
    texts["A"] = "changed"
    spans.clear()
    assert report.refinement.objective == 1


@pytest.mark.parametrize("length,valid", [(65536, True), (65537, False)])
def test_individual_text_length_bound(api, length, valid):
    text = "x"*length
    if valid:
        assert call(api, source_texts={"A": text}, support_spans={"A": {"x": api.SupportSpan(0, length, text)}}).refinement.objective == 1
    else:
        with pytest.raises(ValueError):
            call(api, limit=0, source_texts={"A": text}, support_spans={"A": {"x": api.SupportSpan(0, 1, "x")}})


@pytest.mark.parametrize("extra,valid", [(0, True), (1, False)])
def test_total_text_length_bound(api, extra, valid):
    ids = [str(i) for i in range(17)]
    texts = {str(i): "x"*65536 for i in range(16)}
    texts["16"] = "x"*extra
    args = dict(source_texts=texts, support_spans={}, relevance_weight=1, limit=0)
    if valid:
        assert api.refine_ranked_evidence([R("L", ids)], [], **args).refinement.selected_ids == ()
    else:
        with pytest.raises(ValueError):
            api.refine_ranked_evidence([R("L", ids)], [], **args)


def test_grounding_does_not_drop_disabled_channel_validation(api):
    with pytest.raises(ValueError):
        call(api, channels=[R("L", ["A", "B"]), R("bad", ["Z", "Z"], 0)])
    with pytest.raises(ValueError):
        call(api, channels=[R("L", ["A"]), R("disabled", ["B"], 0)])  # support B is invalid even though zero


def test_boolean_support_is_not_treated_as_witnessed_truth(api):
    with pytest.raises(TypeError):
        call(api, support={"A": {"x": True}})


def test_numpy_integral_offsets_are_supported_without_accepting_bool(api):
    np = pytest.importorskip("numpy")
    assert call(api, support_spans={"A": {"x": api.SupportSpan(np.int64(3), np.int64(8), "到了北京。")}}).refinement.objective == 1
    with pytest.raises(TypeError):
        call(api, support_spans={"A": {"x": api.SupportSpan(np.bool_(True), 8, "到了北京。")}})
