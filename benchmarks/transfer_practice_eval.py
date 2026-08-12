"""Transfer-appropriate practice eval (round 70, Morris et al. 1977).

30 memories (15 semantic facts + 15 episodic events), decayed 32 days;
14 days of daily practice (quota 4, 24h gap):
  - matched: practice_due(kind=SEMANTIC) - sessions focus on the kind the
    upcoming test needs (facts);
  - mixed: practice_due() - no kind preference;
  - none.
Expectation: focused practice retains the target kind best, at the cost
of the other kind (honest tradeoff).
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
    start = utcnow() - timedelta(days=32)
    for i in range(15):
        engine.remember(
            f"事实{i}：稳定事实编号{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"事实{i}"],
            importance=0.4 + 0.5 * (i % 8) / 7,
            strength=0.5 + 0.15 * ((i * 5) % 9) / 8,
            created_at=start,
        )
        engine.remember(
            f"事件{i}：编号{i}的事件记录。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[f"事件{i}"],
            importance=0.4 + 0.5 * (i % 8) / 7,
            strength=0.5 + 0.15 * ((i * 5) % 9) / 8,
            created_at=start,
        )
    return engine


def _simulate(engine: MemoryEngine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow() - timedelta(days=32)
    semantic_reviews = episodic_reviews = 0
    if mode != "none":
        for day in range(14):
            day_now = now + timedelta(days=day)
            due = engine.practice_due(
                limit=4,
                now=day_now,
                min_gap_hours=24.0,
                adaptive_gap=False,
                kind=(MemoryKind.SEMANTIC if mode == "matched" else None),
            )
            for card in due:
                item = engine.backend.get(card["id"])
                if item is None:
                    continue
                if item.kind is MemoryKind.SEMANTIC:
                    semantic_reviews += 1
                else:
                    episodic_reviews += 1
                retrievability = engine.curve.retrievability(item, day_now)
                ok = rng.random() < retrievability
                engine.practice_answer(
                    item.id,
                    item.content if ok else "错误答案",
                    now=day_now,
                )
    final_now = now + timedelta(days=14)
    sem_ret = []
    epi_ret = []
    for item in engine.store.all_active():
        r = engine.curve.retrievability(item, final_now)
        if item.kind is MemoryKind.SEMANTIC:
            sem_ret.append(r)
        else:
            epi_ret.append(r)
    return {
        "mode": mode,
        "semantic_reviews": semantic_reviews,
        "episodic_reviews": episodic_reviews,
        "semantic_mean": round(sum(sem_ret) / len(sem_ret), 3),
        "episodic_mean": round(sum(epi_ret) / len(epi_ret), 3),
        "semantic_retained": sum(1 for r in sem_ret if r >= 0.3),
        "episodic_retained": sum(1 for r in epi_ret if r >= 0.3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "transfer_practice_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "matched": _simulate(copy.deepcopy(base), "matched", args.seed),
        "mixed": _simulate(copy.deepcopy(base), "mixed", args.seed),
        "none": _simulate(copy.deepcopy(base), "none", args.seed),
    }
    report["all_ok"] = bool(
        report["matched"]["semantic_mean"]
        > report["mixed"]["semantic_mean"]
        and report["mixed"]["semantic_mean"]
        > report["none"]["semantic_mean"]
        and report["matched"]["episodic_mean"]
        <= report["mixed"]["episodic_mean"]
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
