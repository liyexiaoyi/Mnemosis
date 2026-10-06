"""Six frozen constructed trajectories, explicit scores; no retrieval/LLM eval."""
from __future__ import annotations
import argparse
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
from fractions import Fraction
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import statistics
import subprocess
import tempfile
import time

from bench_utils import pin_local_src, assert_local_mnemosis
pin_local_src()
LOCAL_MODULE = assert_local_mnemosis()
from mnemosis import MemoryEngine
from mnemosis.types import MemoryItem, MemoryKind, SourceRecord, SourceType
from mnemosis.evidence_selection import EvidenceCandidate, QueryAspect, select_evidence
from verification_utils import ReadOnlyGuard

REPO = Path(__file__).resolve().parent.parent
FIXTURE = REPO / "benchmarks/data/evidence_selection_cases.json"
NOW = datetime(2026, 10, 6, 12, tzinfo=timezone.utc)
METHODS = ("original_topk", "exact_record_dedup_topk", "selector")
DEDUP_FIELDS = ("content", "source", "entity", "scope", "occurred_at", "kind")


def exact_proxy(case, selected):
    """Independent rational oracle; never uses the product scoring helper."""
    q = lambda value: Fraction(str(value))
    chosen = [row for row in case["candidates"] if row["id"] in selected]
    k, lam = case["limit"], q(case["lambda_"])
    weights = {a["id"]: q(a["weight"]) for a in case["aspects"]}
    total = sum(weights.values(), Fraction())
    normalized = {key: value / total for key, value in weights.items()}
    coverage = {key: max((q(row["support"].get(key, 0)) for row in chosen),
                         default=Fraction()) for key in normalized}
    r = sum((q(row["relevance"]) for row in chosen), Fraction()) / k if k else Fraction()
    c = sum((normalized[key] * value for key, value in coverage.items()), Fraction())
    f = lam * r + (1 - lam) * c if k else Fraction()
    return dict(relevance_component=float(r), coverage_component=float(c),
                objective=float(f), objective_exact=str(f),
                aspect_coverage={key: float(value) for key, value in coverage.items()},
                uncovered_aspect_ids=[key for key, value in coverage.items()
                                      if normalized[key] > 0 and value == 0],
                partial_aspect_ids=[key for key, value in coverage.items()
                                    if normalized[key] > 0 and 0 < value < 1])


def snapshot(engine):
    conn = getattr(engine.backend, "_conn", None)
    return deepcopy(dict(
        memories=sorted((i.to_dict() for i in engine.backend.list_items()),
                        key=lambda row: row["id"]),
        links=sorted(engine.backend.all_links()), recall_log=list(engine._recall_log),
        sqlite_full_dump=list(conn.iterdump()) if conn is not None else None))


def baselines(case):
    original = [row["id"] for row in case["candidates"]][:case["limit"]]
    seen, unique = set(), []
    for row in case["candidates"]:
        key = tuple(row[field] for field in DEDUP_FIELDS)
        if key not in seen:
            seen.add(key)
            unique.append(row["id"])
    return original, unique[:case["limit"]]


def evaluate_case(case, backend, root):
    with tempfile.TemporaryDirectory(dir=root) as tmp:
        engine = MemoryEngine(str(Path(tmp) / "memory.sqlite") if backend == "sqlite" else None,
                              auto_warmup=False)
        try:
            ids = {row["id"]: case["name"] + ":" + row["id"] for row in case["candidates"]}
            items = [MemoryItem(
                id=ids[row["id"]], content=row["content"], kind=MemoryKind(row["kind"]),
                source=SourceRecord(SourceType.USER, ref=row["source"],
                                    occurred_at=datetime.fromisoformat(row["occurred_at"])),
                created_at=NOW, last_access_at=NOW, access_count=3,
                context=json.dumps({"entity": row["entity"], "scope": row["scope"]}),
                confidence=.7, retrieval_successes=4, retrieval_failures=2,
                verified_successes=5, verified_failures=1)
                for row in case["candidates"]]
            engine.backend.add_many(items)
            engine.backend.add_link(items[0].id, items[-1].id, .5)
            engine._recall_log.append({"query": "earlier", "ids": [items[0].id]})
            before = snapshot(engine)
            conn = getattr(engine.backend, "_conn", None)
            actual = {i.id: i for i in engine.backend.get_many(list(ids.values()))}
            assert set(actual) == set(ids.values())
            candidates = [EvidenceCandidate(actual[ids[row["id"]]].id,
                                            row["relevance"], row["support"])
                          for row in case["candidates"]]
            aspects = [QueryAspect(a["id"], a["weight"]) for a in case["aspects"]]
            inverse = {value: key for key, value in ids.items()}
            original, dedup = baselines(case)
            rows = []
            for method in METHODS:
                guard = ReadOnlyGuard(conn) if conn is not None else nullcontext()
                with guard:
                    report = select_evidence(candidates, aspects, limit=case["limit"],
                                             relevance_weight=case["lambda_"]) if method == "selector" else None
                selected = ([inverse[i] for i in report.selected_ids] if report else
                            original if method == "original_topk" else dedup)
                proxy = exact_proxy(case, selected)
                if report:
                    for key in ("relevance_component", "coverage_component", "objective"):
                        assert math.isclose(getattr(report, key), proxy[key], abs_tol=1e-12)
                    assert dict(report.aspect_coverage) == proxy["aspect_coverage"]
                required = case["required_ids"]
                complete = set(required).issubset(selected) if required is not None else None
                after = snapshot(engine)
                assert after == before, f"{backend}/{case['name']}/{method} mutated state"
                rows.append(dict(case=case["name"], backend=backend, method=method,
                                 selected_labels=selected, selected_memory_ids=[ids[i] for i in selected],
                                 declared_required_ids=required, required_ids_complete=complete,
                                 proxy=proxy, selector_report=asdict(report) if report else None,
                                 state_unchanged=True, sqlite_guard_checked=conn is not None))
            original_ok, dedup_ok = rows[0]["required_ids_complete"], rows[1]["required_ids_complete"]
            for row in rows:
                value = row["required_ids_complete"]
                row["change_vs_original"] = (int(value) - int(original_ok) if value is not None else None)
                row["change_vs_dedup"] = (int(value) - int(dedup_ok) if value is not None else None)
            labels = [row["id"] for row in case["candidates"]]
            optimum = max(exact_proxy(case, subset)["objective"]
                          for size in range(min(case["limit"], len(labels)) + 1)
                          for subset in combinations(labels, size))
            return rows, dict(case=case["name"], backend=backend, inputs=case,
                              before=before, after=snapshot(engine), state_unchanged=True,
                              optimal_proxy_objective_exhaustive=optimum)
        finally:
            engine.close()


def timings():
    aspects = [QueryAspect("q" + str(j), j + 1) for j in range(32)]
    candidates = [EvidenceCandidate(str(i), (100 - i) / 100,
                                   {a.aspect_id: ((i + 3 * j) % 11) / 10
                                    for j, a in enumerate(aspects)}) for i in range(100)]
    samples, expected = [], None
    for _ in range(7):
        start = time.perf_counter_ns()
        report = select_evidence(candidates, aspects, limit=5)
        samples.append(time.perf_counter_ns() - start)
        if expected is None:
            expected = report
        assert report == expected
    return dict(candidates=100, aspects=32, limit=5, calls=7,
                samples_ns=samples, median_ns=statistics.median(samples),
                selected_ids=list(expected.selected_ids),
                scope="pure function only; no model/database; OS load uncontrolled; not end-to-end speedup")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    output = args.out / "results.json"
    if output.exists():
        parser.error("refusing to replace existing results")
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases, configurations, states = fixture["cases"], [], []
    for backend in ("dict", "sqlite"):
        for case in cases:
            rows, state = evaluate_case(case, backend, args.out)
            configurations.extend(rows)
            states.append(state)
    reference = [row for row in configurations if row["backend"] == "dict"]
    sqlite = [row for row in configurations if row["backend"] == "sqlite"]
    for left, right in zip(reference, sqlite):
        for key in ("case", "method", "selected_labels", "selected_memory_ids", "proxy",
                    "selector_report", "required_ids_complete", "change_vs_original", "change_vs_dedup"):
            assert left[key] == right[key], f"backend mismatch: {key}"
    eligible = sum(case["required_ids"] is not None for case in cases)
    summary = {method: dict(complete=sum(row["required_ids_complete"] is True
                                       for row in reference if row["method"] == method),
                            eligible=eligible) for method in METHODS}
    selector_rows = [row for row in reference if row["method"] == "selector"]
    changes = {baseline: dict(gains=sum(row[key] == 1 for row in selector_rows),
                              losses=sum(row[key] == -1 for row in selector_rows))
               for baseline, key in (("original", "change_vs_original"), ("dedup", "change_vs_dedup"))}
    git = ["git", "-c", "safe.directory=" + REPO.as_posix(), "-C", str(REPO)]
    result = dict(kind=fixture["kind"], source_commit=subprocess.check_output(git + ["rev-parse", "HEAD"], text=True).strip(),
                  harness_worktree_status=subprocess.check_output(git + ["status", "--porcelain"], text=True),
                  local_module=LOCAL_MODULE, fixture_path=str(FIXTURE),
                  independent_trajectories=len(cases), repeated_configurations=len(configurations),
                  eligible_trajectories=eligible, method_summary=summary, selector_changes=changes,
                  backend_parity=True, configurations=configurations, stored_states=states,
                  timing=timings(), python=platform.python_version(), platform=platform.platform(),
                  limits="given scores/support, no recall or answer generation; declared required IDs are only evaluation labels; zero missing support is not factual absence; no accuracy or market-lead claim",
                  complete=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(json.dumps({key: result[key] for key in ("independent_trajectories", "repeated_configurations",
          "method_summary", "selector_changes", "backend_parity", "timing", "complete")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
