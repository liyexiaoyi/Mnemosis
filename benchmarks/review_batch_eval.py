"""Review-batch eval (round 105, Smolen et al. 2016).

30 memories; one review_batch call with 15 successes and 15 failures.
Every detail should reflect the adaptive scheduler exactly: streak,
next review time and retry hours.
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


def _run() -> dict:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    items = []
    for i in range(30):
        item = engine.remember(
            f"批量{i}：条目。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"批量{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        items.append(item)
    answers = [
        {"id": item.id, "success": i % 2 == 0}
        for i, item in enumerate(items)
    ]
    report = engine.review_batch(answers, now=now)
    streak_ok = 0
    next_ok = 0
    for detail in report["details"]:
        item = engine.backend.get(detail["id"])
        if abs(detail["review_streak"] - item.review_streak) < 1e-6:
            streak_ok += 1
        expected = engine.scheduler.next_review_at(item, now)
        if datetime.fromisoformat(detail["next_review_at"]) == expected:
            next_ok += 1
    return {
        "n": report["n"],
        "successes": report["successes"],
        "failures": report["failures"],
        "streak_matches": streak_ok,
        "next_review_matches": next_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "review_batch_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["n"] == 30
        and report["successes"] == 15
        and report["failures"] == 15
        and report["streak_matches"] == 30
        and report["next_review_matches"] == 30
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
