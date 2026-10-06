"""Public API regressions for rounding before weight normalization."""
from fractions import Fraction
import os

import pytest

from mnemosis.evidence_selection import EvidenceCandidate, QueryAspect, select_evidence
from mnemosis.ranked_evidence import RankedChannel, select_ranked_evidence


@pytest.fixture
def numpy():
    try:
        import numpy as np
    except ImportError:
        if os.environ.get("MNEMOSIS_TEST_NUMPY") == "1":
            raise
        pytest.skip("NumPy optional")
    return np


def _run(role, weights):
    if role == "channel":
        report = select_ranked_evidence(
            [RankedChannel("L", ["A"], weights[0]),
             RankedChannel("D", ["B"], weights[1])],
            [], limit=2, relevance_weight=1,
        )
        normalized = tuple(c.normalized_weight for c in report.channels)
        return report, normalized, report.selection
    report = select_evidence(
        [EvidenceCandidate("A", 0, {"X": 1}), EvidenceCandidate("B", 0, {"Y": 1})],
        [QueryAspect("X", weights[0]), QueryAspect("Y", weights[1])],
        limit=2, relevance_weight=0,
    )
    normalized = tuple(report.normalized_aspect_weights[a] for a in ("X", "Y"))
    return report, normalized, report


def _expected(weights):
    # Actual stored scalar values, not decimal literals or product helpers.
    exact = [Fraction(*w.as_integer_ratio()) if hasattr(w, "as_integer_ratio")
             else Fraction(w) for w in weights]
    return tuple(float(w / sum(exact)) for w in exact)


@pytest.mark.parametrize("role", ["channel", "aspect"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("kind", ["float16", "float32", "mixed_left", "mixed_right"])
def test_low_precision_weights_preserve_ratio(numpy, role, reverse, kind):
    if kind == "mixed_left":
        weights = (numpy.float32(2), 3.)
    elif kind == "mixed_right":
        weights = (2., numpy.float32(3))
    else:
        scalar = getattr(numpy, kind)
        weights = (scalar(2), scalar(3))
    if reverse:
        weights = weights[::-1]
    _, normalized, selection = _run(role, weights)
    assert normalized == pytest.approx(_expected(weights), rel=1e-12, abs=0)
    assert selection.selected_ids == (("A", "B") if reverse else ("B", "A"))


@pytest.mark.parametrize("role", ["channel", "aspect"])
@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("kind", ["float16", "float32"])
def test_representable_small_weight_is_not_dropped(numpy, role, reverse, kind):
    weights = ((numpy.float16(1e-4), numpy.float16(1e4)) if kind == "float16"
               else (numpy.float32(1e-30), numpy.float32(1e30)))
    if reverse:
        weights = weights[::-1]
    report, normalized, selection = _run(role, weights)
    expected = _expected(weights)
    assert all(value > 0 for value in expected)
    assert normalized == pytest.approx(expected, rel=1e-12, abs=0)
    assert selection.selected_ids == (("A", "B") if reverse else ("B", "A"))
    assert len(selection.steps) == 2 and selection.steps[1].total_gain > 0
    if role == "channel":
        assert report.underflow_channel_ids == ()
    else:
        assert report.uncovered_aspect_ids == ()


@pytest.mark.parametrize("role", ["channel", "aspect"])
@pytest.mark.parametrize("kind", ["giant_int", "giant_fraction", "tiny_fraction"])
def test_native_extreme_ratios_remain_valid(role, kind):
    if kind == "giant_int":
        weights = (2 * 10**400, 3 * 10**400)
    elif kind == "giant_fraction":
        weights = (Fraction(2 * 10**400), Fraction(3 * 10**400))
    else:
        weights = (Fraction(2, 10**400), Fraction(3, 10**400))
    _, normalized, selection = _run(role, weights)
    assert normalized == pytest.approx((.4, .6), rel=1e-12, abs=0)
    assert selection.selected_ids == ("B", "A")


@pytest.mark.parametrize("role", ["channel", "aspect"])
def test_true_binary64_underflow_has_no_artificial_floor(role):
    report, normalized, selection = _run(role, (1e-308, 1e308))
    assert normalized == (0., 1.)
    assert selection.selected_ids == ("B",)
    if role == "channel":
        assert report.underflow_channel_ids == ("L",)
    else:
        assert report.uncovered_aspect_ids == ("X",)