"""Desirable-difficulty tuning on the zh200 benchmark (round 52).

Builds the 200-session Chinese long-dialogue store (198 events + facts),
then simulates 4 weeks of daily review (quota 6, probabilistic success)
under five strategies: desirable with difficulty targets 0.30 / 0.45 /
0.60, current (most forgotten first), and no review. The final metric is
the real 12-question hit@5 after 4 weeks, not just simulated retention.
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from zh_long_dialogue_eval import build as build_zh200
from zh_long_dialogue_eval import score_questions

from mnemosis import MemoryEngine
from mnemosis.types import utcnow


def _simulate(engine: MemoryEngine, strategy: str, target: float | None,
              seed: int, quota: int, start_offset_days: int = 0) -> dict:
    rng = random.Random(seed)
    now = utcnow() - timedelta(days=start_offset_days)
    reviews = successes = failures = 0
    for day in range(28):
        day_now = now + timedelta(days=day)
        if strategy == "none":
            continue
        due = engine.review_due(
            limit=quota,
            now=day_now,
            desirable_difficulty=(strategy == "desirable"),
            difficulty_target=target if target is not None else 0.45,
        )
        for item in due:
            retrievability = engine.curve.retrievability(item, day_now)
            ok = rng.random() < retrievability
            reviews += 1
            if ok:
                effort = max(0.0, 1.0 - retrievability)
                engine.curve.reinforce_review(
                    item, delta=0.1, now=day_now, effort=effort
                )
                engine.scheduler.record_outcome(item, True, day_now)
                successes += 1
            else:
                engine.scheduler.record_outcome(item, False, day_now)
                failures += 1
    final_day = now + timedelta(days=28)
    items = engine.store.all_active()
    retrievabilities = [engine.curve.retrievability(i, final_day) for i in items]
    retained = sum(1 for r in retrievabilities if r >= 0.3)
    if start_offset_days == 0:
        final = score_questions(
            engine, build_zh200(66)[1], now=final_day,
            temporal_reason=True, reasoning_pack=True,
        )
    else:
        final = {"hit5": None, "hit1": None}
    return {
        "strategy": strategy,
        "target": target,
        "reviews": reviews,
        "successes": successes,
        "failures": failures,
        "success_rate": round(successes / reviews, 3) if reviews else 0.0,
        "retained": retained,
        "mean_retrievability": round(sum(retrievabilities) / len(items), 3),
        "final_hit5": final["hit5"],
        "final_hit1": final["hit1"],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--quota", type=int, default=6)
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="use the 60-memory stress store instead of zh200",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "desirable_tuning_eval.json"),
    )
    args = parser.parse_args()
    if args.synthetic:
        from desirable_difficulty_eval import _base_engine

        base = _base_engine()
        start_offset = 30
    else:
        base, _, _ = build_zh200(66)
        base.sleep()
        start_offset = 0
    strategies = [
        ("desirable", 0.30),
        ("desirable", 0.45),
        ("desirable", 0.60),
        ("current", None),
        ("none", None),
    ]
    report = {}
    for strategy, target in strategies:
        name = f"{strategy}_{target}" if target is not None else strategy
        report[name] = _simulate(
            copy.deepcopy(base), strategy, target, args.seed, args.quota,
            start_offset,
        )
        print(report[name], flush=True)
    best = max(
        (v for k, v in report.items() if v["strategy"] == "desirable"),
        key=lambda v: (v["final_hit5"], v["success_rate"]),
    )
    report["best_desirable"] = best["strategy"] + "_" + str(best["target"])
    print("best:", report["best_desirable"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
