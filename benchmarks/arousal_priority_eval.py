"""Arousal-priority practice eval (round 75, Mather & Sutherland 2011).

30 memories: 15 emotionally arousing + 15 neutral, decayed 32 days;
14 days of daily practice (quota 4, 24h gap):
  - priority: practice_due(arousal_priority=True) rehearses arousing
    memories first within the quota;
  - no_priority: arousal_priority=False;
  - none.
Expectation: priority retains the arousing kind better, at an honest cost
for neutral memories.
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
    start = utcnow() - timedelta(days=32)
    for i in range(15):
        importance = 0.4 + 0.5 * (i % 8) / 7
        strength = 0.5 + 0.15 * ((i * 5) % 9) / 8
        engine.remember(
            f"情绪记忆{i}：那次经历很紧张。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"情绪{i}"],
            affect="negative",
            importance=importance,
            strength=strength,
            created_at=start,
        )
        engine.remember(
            f"中性记忆{i}：普通记录{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"中性{i}"],
            importance=importance,
            strength=strength,
            created_at=start,
        )
    return engine


def _simulate(engine: MemoryEngine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow() - timedelta(days=32)
    if mode != "none":
        for day in range(14):
            day_now = now + timedelta(days=day)
            due = engine.practice_due(
                limit=4,
                now=day_now,
                min_gap_hours=24.0,
                adaptive_gap=False,
                arousal_priority=mode == "priority",
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
    final_now = now + timedelta(days=14)
    aro_ret, neu_ret = [], []
    for item in engine.store.all_active():
        r = engine.curve.retrievability(item, final_now)
        if item.affect == "negative":
            aro_ret.append(r)
        else:
            neu_ret.append(r)
    return {
        "mode": mode,
        "arousal_mean": round(sum(aro_ret) / len(aro_ret), 3),
        "neutral_mean": round(sum(neu_ret) / len(neu_ret), 3),
        "arousal_retained": sum(1 for r in aro_ret if r >= 0.3),
        "neutral_retained": sum(1 for r in neu_ret if r >= 0.3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "arousal_priority_eval.json"),
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
        report["priority"]["arousal_mean"]
        > report["no_priority"]["arousal_mean"]
        and report["no_priority"]["arousal_mean"]
        > report["none"]["arousal_mean"]
        and report["priority"]["neutral_mean"]
        <= report["no_priority"]["neutral_mean"]
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
