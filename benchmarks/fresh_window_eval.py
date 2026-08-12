"""Early consolidation window eval (round 81, Gais et al. 2006).

30 memories: 15 fresh (encoded 2h ago, retrievability ~0.55 - above the
0.5 due threshold, below the 0.65 fresh threshold) + 15 old (32 days).
14 days of daily practice (quota 4, 24h gap):
  - priority: practice_due(fresh_priority=True) rehearses fresh traces
    while they are still consolidating;
  - no_priority: fresh_priority=False (fresh traces wait until they decay
    below 0.5);
  - none.
Expectation: priority retains fresh traces better, at a small honest cost
to old ones.
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
    now = utcnow()
    for i in range(15):
        engine.remember(
            f"新鲜记忆{i}：刚发生的新事{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"新鲜{i}"],
            importance=0.4 + 0.5 * (i % 8) / 7,
            strength=0.55,
            created_at=now - timedelta(hours=2),
        )
        engine.remember(
            f"旧记忆{i}：很久以前的事{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"旧{i}"],
            importance=0.4 + 0.5 * (i % 8) / 7,
            strength=0.55,
            created_at=now - timedelta(days=32),
        )
    return engine


def _simulate(engine: MemoryEngine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow()
    if mode != "none":
        for day in range(14):
            day_now = now + timedelta(days=day)
            due = engine.practice_due(
                limit=4,
                now=day_now,
                min_gap_hours=24.0,
                adaptive_gap=False,
                arousal_priority=False,
                fresh_priority=mode == "priority",
            )
            for card in due:
                item = engine.backend.get(card["id"])
                if item is None:
                    continue
                retrievability = engine.curve.retrievability(item, day_now)
                ok = rng.random() < retrievability
                engine.practice_answer(
                    item.id,
                    item.content if ok else "错误答案",
                    now=day_now,
                )
    final_now = now + timedelta(days=7)
    fresh_ret, old_ret = [], []
    for item in engine.store.all_active():
        r = engine.curve.retrievability(item, final_now)
        if item.content.startswith("新鲜"):
            fresh_ret.append(r)
        else:
            old_ret.append(r)
    return {
        "mode": mode,
        "fresh_mean": round(sum(fresh_ret) / len(fresh_ret), 3),
        "old_mean": round(sum(old_ret) / len(old_ret), 3),
        "fresh_retained": sum(1 for r in fresh_ret if r >= 0.3),
        "old_retained": sum(1 for r in old_ret if r >= 0.3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "fresh_window_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "priority": _simulate(copy.deepcopy(base), "priority", args.seed),
        "no_priority": _simulate(
            copy.deepcopy(base), "no_priority", args.seed
        ),
        "none": _simulate(copy.deepcopy(base), "none", args.seed),
    }
    report["all_ok"] = bool(
        report["priority"]["fresh_mean"]
        > report["no_priority"]["fresh_mean"]
        and report["no_priority"]["fresh_mean"]
        > report["none"]["fresh_mean"]
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
