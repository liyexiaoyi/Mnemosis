"""Generation-effect eval (round 61, Slamecka & Graf 1978).

30 memories decayed 30 days; 14 days of daily practice (quota 4, 48h min
gap):
  - generated: successful attempt phrased in "own words" (paraphrase) and
    generation_bonus=True;
  - verbatim: attempt copies the stored sentence (no bonus);
  - restudy: passive re-read;
  - none.
Generating one's own phrasing should retain more than verbatim copying,
and both should beat restudy and no practice.
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

from testing_effect_eval import _base_engine  # noqa: E402


def _simulate(engine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = engine.store.all_active()[0].created_at
    reviews = successes = failures = generated_count = 0
    for day in range(14):
        day_now = now + timedelta(days=day)
        if mode == "none":
            continue
        due = engine.practice_due(limit=4, now=day_now, min_gap_hours=48.0)
        for card in due:
            item = engine.backend.get(card["id"])
            if item is None:
                continue
            retrievability = engine.curve.retrievability(item, day_now)
            reviews += 1
            if mode == "restudy":
                engine.curve.reinforce(item, delta=0.1, now=day_now)
                engine.scheduler.record_outcome(item, True, day_now)
                engine.backend.update(item)
                successes += 1
                continue
            ok = rng.random() < retrievability
            if mode == "generated":
                attempt = (
                    f"我的回答：{item.content}"
                    if ok
                    else "错误答案"
                )
            else:  # verbatim
                attempt = item.content if ok else "错误答案"
            result = engine.practice_answer(
                item.id, attempt, now=day_now
            )
            if result["success"]:
                successes += 1
                generated_count += int(result.get("generated", False))
            else:
                failures += 1
    final_now = now + timedelta(days=14)
    items = engine.store.all_active()
    retrievabilities = [engine.curve.retrievability(i, final_now) for i in items]
    retained = sum(1 for r in retrievabilities if r >= 0.3)
    baseline = 0.292  # no-practice mean for the fixed seed
    return {
        "mode": mode,
        "reviews": reviews,
        "successes": successes,
        "failures": failures,
        "generated_count": generated_count,
        "retained": retained,
        "mean_retrievability": round(sum(retrievabilities) / len(items), 3),
        "per_review_gain": round(
            (sum(retrievabilities) / len(items) - baseline) / reviews, 5
        ) if reviews else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "generation_effect_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "generated": _simulate(copy.deepcopy(base), "generated", args.seed),
        "verbatim": _simulate(copy.deepcopy(base), "verbatim", args.seed),
        "restudy": _simulate(copy.deepcopy(base), "restudy", args.seed),
        "none": _simulate(copy.deepcopy(base), "none", args.seed),
    }
    report["all_ok"] = bool(
        report["generated"]["mean_retrievability"]
        > report["verbatim"]["mean_retrievability"]
        and report["verbatim"]["mean_retrievability"]
        > report["restudy"]["mean_retrievability"]
        and report["restudy"]["mean_retrievability"]
        > report["none"]["mean_retrievability"]
    )
    for v in report.values():
        print(v, flush=True)
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
