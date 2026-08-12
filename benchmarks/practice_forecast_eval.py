"""Practice-forecast eval (round 90, Smolen et al. 2016).

30 memories with review streaks 0-4 (6 each). A 7-day forecast should
include only traces whose next scheduled review falls inside the window:
streaks 0-3 (12/24/48/96 hours) yes, streak 4 (192 hours) no - 24/30.
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
            f"预报记忆{i}：条目{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"预报{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        item.review_streak = i % 5
        engine.backend.update(item)
    return engine


def _run() -> dict:
    engine = _build_engine()
    now = utcnow()
    forecast = engine.practice_forecast(days=7, now=now)
    exact = 0
    ascending = True
    fields_ok = 0
    prev = None
    for entry in forecast:
        item = engine.backend.get(entry["id"])
        expected = engine.scheduler.next_review_at(item, now)
        if datetime.fromisoformat(entry["due_at"]) == expected:
            exact += 1
        cur = entry["due_at"]
        if prev is not None and cur < prev:
            ascending = False
        prev = cur
        if all(
            key in entry
            for key in (
                "id", "cue", "due_at", "retrievability",
                "success_rate", "kind",
            )
        ):
            fields_ok += 1
    return {
        "forecast_count": len(forecast),
        "expected_count": 24,
        "exact_due": exact,
        "ascending": int(ascending),
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "practice_forecast_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["forecast_count"] == report["expected_count"]
        and report["exact_due"] == report["expected_count"]
        and report["ascending"] == 1
        and report["fields_ok"] == report["expected_count"]
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
