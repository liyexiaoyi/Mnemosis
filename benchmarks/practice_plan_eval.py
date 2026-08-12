"""Practice-plan eval (round 80).

30 memories in three scheduler states (failed streak 0 / success streak 1
/ double-success streak 2). practice_plan() should expose, for every due
card, the exact next review time the scheduler would use, plus current
retrievability and historical success rate, so agents can plan around the
memory system (Smolen et al., 2016 adaptive spacing).
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
        item = engine.remember(
            f"计划记忆{i}：条目{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"计划{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        item.review_streak = i % 3
        engine.backend.update(item)
    return engine


def _run() -> dict:
    engine = _build_engine()
    now = utcnow()
    plan = engine.practice_plan(limit=30, now=now)
    exact = 0
    correct_horizon = 0
    fields_ok = 0
    for entry in plan:
        item = engine.backend.get(entry["id"])
        expected = engine.scheduler.next_review_at(item, now)
        if datetime.fromisoformat(entry["next_review_at"]) == expected:
            exact += 1
        hours = (
            datetime.fromisoformat(entry["next_review_at"]) - now
        ).total_seconds() / 3600.0
        expected_hours = 12 * (2 ** item.review_streak)
        if abs(hours - expected_hours) < 0.001:
            correct_horizon += 1
        if all(
            key in entry
            for key in (
                "id", "cue", "next_review_at", "retrievability",
                "success_rate", "kind",
            )
        ):
            fields_ok += 1
    return {
        "planned": len(plan),
        "exact_next_review": exact,
        "correct_horizon": correct_horizon,
        "fields_ok": fields_ok,
        "total": 30,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "practice_plan_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["planned"] == 30
        and report["exact_next_review"] == 30
        and report["correct_horizon"] == 30
        and report["fields_ok"] == 30
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
