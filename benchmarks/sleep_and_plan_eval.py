"""Sleep-and-plan eval (round 110, Stickgold & Walker 2013).

10 stores, each with 5 weak-important semantic traces, 5 low-importance
due traces and 5 fresh strong ones. sleep_and_plan should replay the
weak-important ones (count matches manual sleep), leave the low-importance
ones due (so plan/forecast are non-empty) and return a valid summary.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(5):
        engine.remember(
            f"w{seed}-{i} important",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"w{seed}-{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=60),
            auto_cues=False,
        )
    for i in range(5):
        engine.remember(
            f"d{seed}-{i} due",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"d{seed}-{i}"],
            importance=0.3,
            strength=0.2,
            created_at=now - timedelta(days=30),
            auto_cues=False,
        )
    for i in range(5):
        engine.remember(
            f"f{seed}-{i} fresh",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"f{seed}-{i}"],
            importance=0.7,
            strength=0.9,
            created_at=now - timedelta(days=1),
            auto_cues=False,
        )
    return engine


def _run() -> dict:
    replay_ok = 0
    plan_ok = 0
    forecast_ok = 0
    summary_ok = 0
    for seed in range(10):
        engine = _store(seed)
        now = utcnow()
        manual = engine.sleep(now=now)
        engine2 = _store(seed)
        result = engine2.sleep_and_plan(days=7, now=now)
        replay_ok += int(result["weak_replayed"] == manual.weak_replayed)
        plan_ok += int(len(result["plan"]) >= 5)
        forecast_ok += int(len(result["forecast"]) >= 5)
        summary_ok += int("weak_replayed" in result["sleep_summary"])
    return {
        "stores": 10,
        "replay_match": replay_ok,
        "plan_nonempty": plan_ok,
        "forecast_nonempty": forecast_ok,
        "summary_ok": summary_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "sleep_and_plan_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(v == 10 for k, v in report.items() if k != "stores")
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
