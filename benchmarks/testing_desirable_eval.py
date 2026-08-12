"""Testing effect x desirable difficulty combined eval (round 55).

14 days of daily practice sessions (quota 4) on 30 decayed memories:
  - practice + desirable: retrieval practice cards ordered by desirable
    difficulty (closest to target 0.45);
  - practice + forgotten: practice cards ordered most-forgotten first;
  - restudy: passive re-read;
  - none.
Expect practice+desirable >= practice+forgotten > restudy > none.
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
        if mode == "none":
            continue
        desirable = mode.startswith("practice_desirable")
        if mode.startswith("practice"):
            due = engine.practice_due(
                limit=4, now=day_now, desirable_difficulty=desirable
            )
        else:
            due = engine.practice_due(
                limit=4, now=day_now, desirable_difficulty=False
            )
        for card in due:
            item = engine.backend.get(card["id"])
            if item is None:
                continue
            reviews += 1
            if mode.startswith("practice"):
                retrievability = engine.curve.retrievability(item, day_now)
                ok = rng.random() < retrievability
                attempt = item.content if ok else "错误答案"
                result = engine.practice_answer(item.id, attempt, now=day_now)
                if result["success"]:
                    successes += 1
                else:
                    failures += 1
            else:  # restudy
                engine.curve.reinforce(item, delta=0.1, now=day_now)
                engine.scheduler.record_outcome(item, True, day_now)
                engine.backend.update(item)
                successes += 1
    final_now = now + timedelta(days=14)
    items = engine.store.all_active()
    retrievabilities = [engine.curve.retrievability(i, final_now) for i in items]
    retained = sum(1 for r in retrievabilities if r >= 0.3)
    return {
        "mode": mode,
        "reviews": reviews,
        "successes": successes,
        "failures": failures,
        "retained": retained,
        "mean_retrievability": round(sum(retrievabilities) / len(items), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "testing_desirable_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    modes = [
        "practice_desirable",
        "practice_forgotten",
        "restudy",
        "none",
    ]
    report = {}
    for mode in modes:
        report[mode] = _simulate(copy.deepcopy(base), mode, args.seed)
        print(report[mode], flush=True)
    report["all_ok"] = bool(
        report["practice_desirable"]["mean_retrievability"]
        >= report["practice_forgotten"]["mean_retrievability"]
        and report["practice_forgotten"]["mean_retrievability"]
        > report["restudy"]["mean_retrievability"]
        and report["restudy"]["mean_retrievability"]
        > report["none"]["mean_retrievability"]
    )
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
