"""Unknown annotations cannot establish absence of required evidence."""
from itertools import combinations, product

import pytest

from evidence_fixtures import FixedAnnotator, results
from mnemosis.evidence_recall import select_from_snapshot


def row(memory_id, aspect_id, verdict, quote=None):
    return dict(memory_id=memory_id, aspect_id=aspect_id, verdict=verdict, quote=quote)


@pytest.mark.parametrize("unknown", ["omitted", "explicit"])
def test_unannotated_date_is_undetermined_not_proved_absent(unknown):
    rows = [row("A", "a0", "supported", "Osaka")]
    if unknown == "explicit":
        rows.append(row("C", "a1", "unknown"))
    report = select_from_snapshot("Where and when was the trip?", results(),
                                  annotator=FixedAnnotator(rows=rows), top_k=2)
    assert report.status == "undetermined"
    assert report.reason == "incomplete_support"
    assert report.results == ()
    assert report.annotation_status == "partial"
    # The nested selector still describes the pessimistic supplied-input run.
    assert report.selector.status == "infeasible"
    assert report.selector.selection is None
    assert report.selector.visited_nodes == 0


def test_explicitly_rejected_role_still_proves_infeasible_with_other_unknowns():
    rows = [row(m, "a1", "not_supported") for m in ("A", "B", "C")]
    report = select_from_snapshot("trip?", results(), annotator=FixedAnnotator(rows=rows))
    assert report.status == "infeasible"
    assert report.annotation_status == "partial"
    assert report.results == ()


def test_capacity_failure_with_complete_annotations_remains_infeasible():
    report = select_from_snapshot("trip?", results(), annotator=FixedAnnotator(), top_k=1)
    assert report.status == "infeasible"
    assert report.annotation_status == "complete"


def test_unknown_support_never_turns_into_positive_evidence_at_zero_budget():
    report = select_from_snapshot("trip?", results(), top_k=2, search_budget=0,
        annotator=FixedAnnotator(rows=[row("A", "a0", "supported", "Osaka")]))
    assert report.status == "undetermined" and report.results == ()
    assert report.selector.visited_nodes == 0 and report.selector.search_budget == 0
    assert report.support == {"A": {"a0": 1}}


def test_known_witness_survives_unknown_other_pairs_and_zero_budget():
    rows = [row("A", "a0", "supported", "Osaka"), row("C", "a1", "supported", "October")]
    report = select_from_snapshot("trip?", [results()[0], results()[2]],
                                  annotator=FixedAnnotator(rows=rows), top_k=2, search_budget=0)
    assert report.status == "feasible"
    assert [r.item.id for r in report.results] == ["A", "C"]
    assert report.annotation_status == "partial"


def test_small_ternary_annotations_never_make_an_unsound_claim():
    # Enumerate every 2-record / 2-role table. 0 and 1 are known annotations;
    # None permits either completion. Independently enumerate admissible sets.
    candidates = [results()[0], results()[2]]
    pairs = [(m, a) for m in ("A", "C") for a in ("a0", "a1")]
    for values in product((None, 0, 1), repeat=4):
        rows = [row(m, a, "supported" if v else "not_supported",
                    candidates[0 if m == "A" else 1].item.content if v else None)
                for (m, a), v in zip(pairs, values) if v is not None]
        for capacity in (1, 2):
            report = select_from_snapshot("trip?", candidates, top_k=capacity,
                                          annotator=FixedAnnotator(rows=rows))
            if not rows:
                assert report.status == "annotation_failed"
                continue
            sets = [s for size in range(1, capacity + 1)
                    for s in combinations((0, 1), size)]
            lower_witness = any(all(any(values[2*i+a] == 1 for i in s)
                                    for a in (0, 1)) for s in sets)
            upper_witness = any(all(any(values[2*i+a] != 0 for i in s)
                                    for a in (0, 1)) for s in sets)
            assert (report.status == "feasible") == lower_witness, (values, capacity)
            if report.status == "infeasible":
                assert not upper_witness, (values, capacity)
            if report.status == "feasible":
                selected = {r.item.id for r in report.results}
                assert all(any(m in selected and v == 1
                               for (m, role), v in zip(pairs, values) if role == a)
                           for a in ("a0", "a1")), (values, capacity)
            assert report.selector.visited_nodes <= report.selector.search_budget
