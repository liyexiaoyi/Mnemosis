"""Practice-report difficulty stats eval (round 100).

30 memories with varied strength; a practice_report round over all of
them. The report's difficulty block should match a manual computation of
the session's retrievability (mean/min/max) and expose mean_difficulty =
1 - mean_retrievability.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _run() -> dict:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(30):
        engine.remember(
            f"难度条目{i}：内容{i}。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"难度条目{i}"],
            importance=0.8,
            strength=0.2 + 0.025 * i,
            created_at=now - timedelta(days=20),
        )
    answers = [
        {"id": item.id, "attempt": "测试"}
        for item in engine.store.all_active()
    ]
    report = engine.practice_report(answers, now=now)
    manual = [
        engine.curve.retrievability(item, now)
        for item in engine.store.all_active()
    ]
    diff = report["difficulty"]
    mean_ok = abs(
        diff["mean_retrievability"] - sum(manual) / len(manual)
    ) < 0.001
    min_ok = abs(diff["min_retrievability"] - min(manual)) < 0.001
    max_ok = abs(diff["max_retrievability"] - max(manual)) < 0.001
    diff_ok = abs(
        diff["mean_difficulty"] - (1.0 - diff["mean_retrievability"])
    ) < 0.001
    return {
        "n": diff["n"],
        "mean_matches": int(mean_ok),
        "min_matches": int(min_ok),
        "max_matches": int(max_ok),
        "difficulty_ok": int(diff_ok),
        "mean_difficulty": diff["mean_difficulty"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "report_difficulty_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["n"] == 30
        and report["mean_matches"] == 1
        and report["min_matches"] == 1
        and report["max_matches"] == 1
        and report["difficulty_ok"] == 1
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
