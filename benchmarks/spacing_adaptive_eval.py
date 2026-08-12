"""Success-rate adaptive practice spacing (round 57).

14 days of daily practice (quota 4) on 30 decayed memories:
  - adaptive: 24h base gap, struggling items (success rate < 0.5) get a
    0.6x gap, strong items (>= 0.9) get 1.3x;
  - fixed:    flat 24h gap;
  - massed:   no gap.
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

from testing_effect_eval import _base_engine


def _simulate(engine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = engine.store.all_active()[0].created_at
    reviews = successes = failures = 0
    for day in range(14):
        day_now = now + timedelta(days=day)
        if mode == "massed":
            due = engine.practice_due(
                limit=4, now=day_now, min_gap_hours=0
            )
        else:
            due = engine.practice_due(
                limit=4,
                now=day_now,
                min_gap_hours=36.0,
                adaptive_gap=(mode == "adaptive"),
            )
        for card in due:
            item = engine.backend.get(card["id"])
            if item is None:
                continue
            reviews += 1
            retrievability = engine.curve.retrievability(item, day_now)
            ok = rng.random() < retrievability
            attempt = item.content if ok else "错误答案"
            result = engine.practice_answer(item.id, attempt, now=day_now)
            if result["success"]:
                successes += 1
            else:
                failures += 1
    final_now = now + timedelta(days=14)
    items = engine.store.all_active()
    retrievabilities = [engine.curve.retrievability(i, final_now) for i in items]
    retained = sum(1 for r in retrievabilities if r >= 0.3)
    baseline = 0.292
    per_review_gain = (
        (sum(retrievabilities) / len(items) - baseline) / reviews
        if reviews
        else 0.0
    )
    return {
        "mode": mode,
        "reviews": reviews,
        "successes": successes,
        "failures": failures,
        "retained": retained,
        "mean_retrievability": round(sum(retrievabilities) / len(items), 3),
        "per_review_gain": round(per_review_gain, 5),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "spacing_adaptive_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {}
    for mode in ("adaptive", "fixed", "massed"):
        report[mode] = _simulate(copy.deepcopy(base), mode, args.seed)
        print(report[mode], flush=True)
    report["all_ok"] = bool(
        report["adaptive"]["per_review_gain"]
        >= report["fixed"]["per_review_gain"]
        and report["fixed"]["per_review_gain"]
        > report["massed"]["per_review_gain"]
    )
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
