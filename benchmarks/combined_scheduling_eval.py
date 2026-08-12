"""Combined scheduling eval (round 82).

30 memories: 10 fresh (2h), 10 emotionally arousing (old), 10 neutral
(5 semantic + 5 episodic, old). 14 days of daily practice (quota 4, 24h
gap):
  - combined: kind/arousal/fresh/interleave/vary_cues all enabled;
  - baseline: all scheduling flags disabled.
Combined uses the robust subset: arousal_priority + interleave + vary_cues
ON, fresh_priority OFF (the fresh window is workload-specific - in a mixed
store it reheares traces before they are retrievable enough and wastes
quota). Expectation: the combined pipeline keeps the arousal benefit
without losing overall retention.
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
    for i in range(10):
        engine.remember(
            f"新鲜记忆{i}：刚发生的新事{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"新鲜{i}"],
            importance=0.5,
            strength=0.55,
            created_at=now - timedelta(hours=2),
        )
        engine.remember(
            f"情绪记忆{i}：那次很紧张{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"情绪{i}"],
            affect="negative",
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=32),
        )
    for i in range(5):
        engine.remember(
            f"中性事实{i}：稳定记录{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"事实{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=32),
        )
        engine.remember(
            f"中性事件{i}：普通经过{i}。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[f"事件{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=32),
        )
    return engine


def _simulate(engine: MemoryEngine, combined: bool, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow()
    for day in range(14):
        day_now = now + timedelta(days=day)
        due = engine.practice_due(
            limit=4,
            now=day_now,
            min_gap_hours=24.0,
            adaptive_gap=False,
            arousal_priority=combined,
            fresh_priority=False,
            interleave=combined,
            vary_cues=combined,
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
    fresh, aro, neu = [], [], []
    for item in engine.store.all_active():
        r = engine.curve.retrievability(item, final_now)
        if item.content.startswith("新鲜"):
            fresh.append(r)
        elif item.affect == "negative":
            aro.append(r)
        else:
            neu.append(r)
    return {
        "combined": combined,
        "fresh_mean": round(sum(fresh) / len(fresh), 3),
        "arousal_mean": round(sum(aro) / len(aro), 3),
        "neutral_mean": round(sum(neu) / len(neu), 3),
        "retained": sum(
            1
            for item in engine.store.all_active()
            if engine.curve.retrievability(item, final_now) >= 0.3
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "combined_scheduling_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "combined": _simulate(copy.deepcopy(base), True, args.seed),
        "baseline": _simulate(copy.deepcopy(base), False, args.seed),
    }
    report["all_ok"] = bool(
        report["combined"]["arousal_mean"]
        >= report["baseline"]["arousal_mean"]
        and report["combined"]["retained"]
        >= report["baseline"]["retained"]
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
