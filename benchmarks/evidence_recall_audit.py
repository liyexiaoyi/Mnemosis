"""Independent result accounting, without model calls or evaluator helpers."""
from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
from statistics import median


def summarize(rows):
    answerable = [r for r in rows if r["question"].get("expected")]
    systems = {}
    complete = {}
    for name in ("A", "B", "C"):
        all_values, hit_values, multi, single = [], [], [], []
        for row in answerable:
            expected = set(row["question"]["expected"])
            actual = [r["item"]["content"] for r in row[name]["results"]]
            all_found = expected.issubset(actual)
            all_values.append(all_found)
            hit_values.append(bool(actual) and actual[0] in expected)
            (multi if len(expected) > 1 else single).append(all_found)
        latencies = sorted(r[name]["seconds"] * 1000 for r in rows)
        systems[name] = {"all": sum(all_values), "hit1": sum(hit_values),
            "single_all": sum(single), "single_questions": len(single),
            "multi_all": sum(multi), "multi_questions": len(multi),
            "median_ms": median(latencies) if latencies else None,
            "p95_ms": latencies[max(0, math.ceil(.95 * len(latencies)) - 1)] if latencies else None}
        complete[name] = all_values
    result = {"questions": len(rows), "answerable": len(answerable), "systems": systems,
              "statuses": dict(Counter(r["report"]["status"] for r in rows))}
    for first, second in (("B", "A"), ("C", "B"), ("C", "A")):
        result[f"{first}_vs_{second}"] = {
            "gains": sum(x and not y for x,y in zip(complete[first], complete[second])),
            "losses": sum(y and not x for x,y in zip(complete[first], complete[second]))}
    pool_complete, lost = 0, 0
    for row in answerable:
        expected = set(row["question"]["expected"])
        pool = {r["item"]["content"] for r in row["candidates"]}
        chosen = {r["item"]["content"] for r in row["C"]["results"]}
        pool_complete += expected.issubset(pool)
        lost += expected.issubset(pool) and not expected.issubset(chosen)
        # Validate the evaluator's stored individual flags, if present.
        for name in ("A", "B", "C"):
            actual = [r["item"]["content"] for r in row[name]["results"]]
            if "metrics" in row[name]:
                assert row[name]["metrics"] == {"all": expected.issubset(actual),
                    "hit1": bool(actual) and actual[0] in expected,
                    "any": bool(expected.intersection(actual))}
    result["pool_complete"] = pool_complete
    result["pool_complete_but_C_incomplete"] = lost
    result["annotation_statuses"] = dict(Counter(r["report"].get("annotation_status", "unknown") for r in rows))
    return result


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    rows = [json.loads(line) for line in Path(args.results).read_text(encoding="utf8").splitlines() if line]
    result = summarize(rows)
    with Path(args.output).open("x", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
