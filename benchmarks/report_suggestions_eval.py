"""Practice-report review-suggestions eval (round 91).

30 memories; a practice_report round with 15 correct and 15 wrong
attempts. Every detail should carry the exact next review time from the
scheduler and a human-friendly retry_hours (success ~24h, failure ~12h).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(30):
        engine.remember(
            f"条目{i}：内容编号{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"条目{i}"],
            importance=0.8,
            strength=0.5,
            created_at=now - timedelta(days=20),
        )
    return engine


def _run() -> dict:
    engine = _build_engine()
    now = utcnow()
    answers = []
    for i, item in enumerate(engine.store.all_active()):
        answers.append(
            {
                "id": item.id,
                "attempt": item.content if i % 2 == 0 else "完全错误",
            }
        )
    report = engine.practice_report(answers, now=now)
    exact = 0
    buckets = 0
    for detail in report["details"]:
        item = engine.backend.get(detail["id"])
        expected = engine.scheduler.next_review_at(item, now)
        if datetime.fromisoformat(detail["next_review_at"]) == expected:
            exact += 1
        expected_hours = 24.0 if detail["success"] else 12.0
        if abs(detail["retry_hours"] - expected_hours) < 0.1:
            buckets += 1
    return {
        "n": len(report["details"]),
        "exact_next_review": exact,
        "correct_horizon": buckets,
        "successes": report["successes"],
        "failures": report["failures"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "report_suggestions_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["exact_next_review"] == report["n"]
        and report["correct_horizon"] == report["n"]
        and report["successes"] == 15
        and report["failures"] == 15
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
