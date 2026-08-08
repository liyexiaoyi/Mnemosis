"""Review-score priority eval (round 101).

30 memories: 10 high-importance fading, 10 mid-importance weak, 10
low-importance strong. 10 days of practice (quota 3, 24h gap):
  - score: practice_due(review_score_priority=True) orders by
    importance x forgetting;
  - default: importance-first ordering.
Expectation: score mode protects more important content (importance-
weighted retention), possibly at a small total-retention cost.
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
    now = utcnow()
    groups = [
        (0.9, 0.4, 40, "高"),
        (0.6, 0.5, 20, "中"),
        (0.4, 0.7, 1, "低"),
    ]
    for g, (imp, strength, days, tag) in enumerate(groups):
        for i in range(10):
            engine.remember(
                f"{tag}重要记忆{g}{i}：条目。",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[f"score{g}{i}"],
                importance=imp,
                strength=strength,
                created_at=now - timedelta(days=days),
                auto_cues=False,
            )
    return engine


def _simulate(engine: MemoryEngine, score_mode: bool, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow()
    for day in range(10):
        day_now = now + timedelta(days=day)
        due = engine.practice_due(
            limit=3,
            now=day_now,
            min_gap_hours=24.0,
            adaptive_gap=False,
            desirable_difficulty=False,
            arousal_priority=False,
            fresh_priority=False,
            review_score_priority=score_mode,
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
    total = 0
    weighted = 0.0
    for item in engine.store.all_active():
        r = engine.curve.retrievability(item, final_now)
        if r >= 0.3:
            total += 1
            weighted += item.importance
    return {
        "score_mode": score_mode,
        "retained": total,
        "importance_weighted_retained": round(weighted, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "review_score_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "score": _simulate(copy.deepcopy(base), True, args.seed),
        "default": _simulate(copy.deepcopy(base), False, args.seed),
    }
    report["all_ok"] = bool(
        report["score"]["importance_weighted_retained"]
        > report["default"]["importance_weighted_retained"]
        and report["score"]["retained"]
        >= report["default"]["retained"] - 2
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
