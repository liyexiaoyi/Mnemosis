"""Retrieval-induced forgetting eval (round 59, Anderson et al. 1994).

24 memories in 3 categories (8 each): items 0-3 are practice targets,
4-7 are competitors sharing the same cue. 14 days of daily practice on
the 12 targets only (quota 4, 48h min gap):
  - suppressed: practice_answer(suppress_competitors=True) lowers the
    competitors' strength after each successful recall;
  - unsuppressed: practice_answer(suppress_competitors=False);
  - none.
End-of-run query per category cue checks whether a practised target ranks
first (discriminability), plus mean retrievability of targets/competitors.
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

CATEGORIES = ["颜色", "水果", "城市"]
PER_CAT = 8


def _base_engine(start) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    idx = 0
    for cat in CATEGORIES:
        for i in range(PER_CAT):
            importance = 0.4 + 0.5 * ((idx * 3) % 8) / 7
            strength = 0.5 + 0.15 * ((idx * 5) % 9) / 8
            engine.remember(
                f"{cat}记忆{idx}：第{i}个答案内容是{idx}号。",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[cat, f"记忆{idx}"],
                importance=importance,
                strength=strength,
                created_at=start,
                auto_cues=False,
            )
            idx += 1
    return engine


def _item_index(item) -> int:
    for cue in item.cues:
        if cue.startswith("记忆"):
            return int(cue[2:])
    return 0


def _simulate(
    engine: MemoryEngine, mode: str, seed: int, start
) -> dict:
    rng = random.Random(seed)
    targets = []
    for item in engine.store.all_active():
        i = _item_index(item)
        # target = first four of each category by content index
        if i % PER_CAT < 4:
            targets.append(item.id)
    reviews = successes = failures = suppressed_total = 0
    if mode != "none":
        for day in range(14):
            day_now = start + timedelta(days=day)
            due = engine.practice_due(
                limit=6, now=day_now, min_gap_hours=24.0
            )
            for card in due:
                item = engine.backend.get(card["id"])
                if item is None:
                    continue
                retrievability = engine.curve.retrievability(item, day_now)
                if card["id"] in targets:
                    reviews += 1
                ok = rng.random() < retrievability
                attempt = item.content if ok else "错误答案"
                result = engine.practice_answer(
                    item.id,
                    attempt,
                    now=day_now,
                    suppress_competitors=mode == "suppressed",
                )
                if result["success"]:
                    if card["id"] in targets:
                        successes += 1
                    suppressed_total += result.get("suppressed", 0)
                else:
                    if card["id"] in targets:
                        failures += 1
    final_now = start + timedelta(days=14)
    target_ret = []
    competitor_ret = []
    for item in engine.store.all_active():
        r = engine.curve.retrievability(item, final_now)
        i = _item_index(item)
        if i % PER_CAT < 4:
            target_ret.append(r)
        else:
            competitor_ret.append(r)
    # discriminability: query each category cue, is a target first?
    target_first = 0
    first_target_ranks = []
    for cat in CATEGORIES:
        results = engine.recall(cat, top_k=8, now=final_now)
        for rank, res in enumerate(results, start=1):
            if _item_index(res.item) % PER_CAT < 4:
                first_target_ranks.append(rank)
                if rank == 1:
                    target_first += 1
                break
    report = {
        "mode": mode,
        "reviews": reviews,
        "successes": successes,
        "failures": failures,
        "suppressed_total": suppressed_total,
        "target_first": target_first,
        "target_first_ratio": round(target_first / len(CATEGORIES), 3),
        "target_avg_rank": round(
            sum(first_target_ranks) / len(first_target_ranks), 3
        ) if first_target_ranks else None,
        "target_mean": round(sum(target_ret) / len(target_ret), 3),
        "competitor_mean": round(
            sum(competitor_ret) / len(competitor_ret), 3
        ),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "interference_suppression_eval.json"
        ),
    )
    args = parser.parse_args()
    start = utcnow() - timedelta(days=32)
    base = _base_engine(start)
    report = {
        "suppressed": _simulate(
            copy.deepcopy(base), "suppressed", args.seed, start
        ),
        "unsuppressed": _simulate(
            copy.deepcopy(base), "unsuppressed", args.seed, start
        ),
        "none": _simulate(copy.deepcopy(base), "none", args.seed, start),
    }
    report["all_ok"] = bool(
        report["suppressed"]["target_avg_rank"]
        <= report["unsuppressed"]["target_avg_rank"]
        and report["suppressed"]["target_mean"]
        >= report["unsuppressed"]["target_mean"]
        and report["unsuppressed"]["target_mean"]
        > report["none"]["target_mean"]
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
