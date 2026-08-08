"""Testing-effect evaluation (round 54, Roediger & Karpicke 2006).

30 memories decayed 30 days; 14 days of daily sessions (quota 4):
  - practice: agent attempts retrieval from cues (probabilistic by
    retrievability), gets feedback, effort-scaled reinforcement;
  - restudy:  content is re-read, plain reinforcement (no effort gain);
  - none.
Active retrieval practice should retain more than restudy, and both more
than no practice.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _base_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    start = utcnow() - timedelta(days=30)
    for i in range(30):
        importance = 0.4 + 0.5 * (i % 8) / 7
        strength = 0.5 + 0.15 * ((i * 5) % 9) / 8
        engine.remember(
            f"练习记忆{i}：阿丽喜欢的颜色编号是{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"颜色{i}", f"编号{i}"],
            importance=importance,
            strength=strength,
            created_at=start,
        )
    return engine


def _simulate(engine: MemoryEngine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow() - timedelta(days=30)
    sessions = reviews = successes = failures = 0
    for day in range(14):
        day_now = now + timedelta(days=day)
        if mode == "none":
            continue
        sessions += 1
        due = engine.practice_due(limit=4, now=day_now)
        for card in due:
            item = engine.backend.get(card["id"])
            if item is None:
                continue
            retrievability = engine.curve.retrievability(item, day_now)
            reviews += 1
            if mode == "practice":
                ok = rng.random() < retrievability
                attempt = item.content if ok else "错误答案"
                result = engine.practice_answer(item.id, attempt, now=day_now)
                if result["success"]:
                    successes += 1
                else:
                    failures += 1
            else:  # restudy: passive re-read, plain reinforcement
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
        "sessions": sessions,
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
        default=os.path.join(_BENCH, "results", "testing_effect_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "practice": _simulate(copy.deepcopy(base), "practice", args.seed),
        "restudy": _simulate(copy.deepcopy(base), "restudy", args.seed),
        "none": _simulate(copy.deepcopy(base), "none", args.seed),
    }
    for v in report.values():
        print(v, flush=True)
    report["all_ok"] = bool(
        report["practice"]["mean_retrievability"]
        > report["restudy"]["mean_retrievability"]
        and report["practice"]["retained"]
        >= report["restudy"]["retained"]
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
