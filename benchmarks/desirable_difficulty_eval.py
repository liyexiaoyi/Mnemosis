"""Desirable-difficulty review scheduling evaluation (round 51).

60 memories with varied importance/strength decayed for 30 days, then 4
weeks of daily review (quota 6) under three strategies:
  - desirable: pick due items closest to difficulty target 0.45;
  - current:   pick due items most forgotten first;
  - none:      no review.
Each review succeeds with probability = retrievability (Bjork: hard-but-
successful retrievals strengthen more; failed retrievals do not).
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

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _base_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    start = utcnow() - timedelta(days=30)
    for i in range(60):
        importance = 0.3 + 0.6 * (i % 10) / 9
        strength = 0.45 + 0.2 * ((i * 7) % 11) / 10
        engine.remember(
            f"复习记忆{i}：阿丽喜欢颜色编号{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"颜色{i}"],
            importance=importance,
            strength=strength,
            created_at=start,
        )
    return engine


def _simulate(engine: MemoryEngine, strategy: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow() - timedelta(days=30)
    reviews = successes = failures = 0
    for day in range(28):
        day_now = now + timedelta(days=day)
        if strategy == "none":
            continue
        due = engine.review_due(
            limit=6,
            now=day_now,
            desirable_difficulty=(strategy == "desirable"),
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
    final_now = now + timedelta(days=28)
    items = engine.store.all_active()
    retrievabilities = [engine.curve.retrievability(i, final_now) for i in items]
    retained = sum(1 for r in retrievabilities if r >= 0.3)
    return {
        "strategy": strategy,
        "reviews": reviews,
        "successes": successes,
        "failures": failures,
        "success_rate": round(successes / reviews, 3) if reviews else 0.0,
        "retained": retained,
        "mean_retrievability": round(sum(retrievabilities) / len(items), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "desirable_difficulty_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "desirable": _simulate(copy.deepcopy(base), "desirable", args.seed),
        "current": _simulate(copy.deepcopy(base), "current", args.seed),
        "none": _simulate(copy.deepcopy(base), "none", args.seed),
    }
    for v in report.values():
        print(v, flush=True)
    report["all_ok"] = bool(
        report["desirable"]["retained"] >= report["current"]["retained"]
        and report["desirable"]["success_rate"]
        >= report["current"]["success_rate"]
        and report["current"]["retained"] >= report["none"]["retained"]
    )
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
