"""Interleaving vs blocked practice eval (round 58, Rohrer & Taylor 2007).

30 memories across 3 categories (10 each), decayed 30 days; 14 days of
daily practice (quota 4, 48h min gap):
  - interleaved: practice_due(interleave=True)  - adjacent cards avoid
    the same category;
  - blocked:     practice_due(interleave=False) - native due ordering;
  - none.
Measures the real scheduling property (same-category adjacent-pair rate,
lower is better) plus retention: interleaved should mix categories with
no worse retention than blocked, and both should beat no practice.
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


def _base_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    start = utcnow() - timedelta(days=30)
    idx = 0
    for cat in CATEGORIES:
        for i in range(10):
            importance = 0.4 + 0.5 * ((idx * 3) % 8) / 7
            strength = 0.5 + 0.15 * ((idx * 5) % 9) / 8
            engine.remember(
                f"{cat}记忆{idx}：第{i}个答案内容是{idx}号。",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[cat, f"{cat}{i}"],
                importance=importance,
                strength=strength,
                created_at=start,
            )
            idx += 1
    return engine


def _simulate(engine: MemoryEngine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow() - timedelta(days=30)
    reviews = successes = failures = 0
    same_cat_pairs = total_pairs = 0
    interleave = mode == "interleaved"
    for day in range(14):
        day_now = now + timedelta(days=day)
        if mode == "none":
            continue
        due = engine.practice_due(
            limit=4,
            now=day_now,
            min_gap_hours=48.0,
            interleave=interleave,
            arousal_priority=False,
            fresh_priority=False,
        )
        cats = []
        for card in due:
            item = engine.backend.get(card["id"])
            if item is None:
                continue
            cats.append(item.cues[0] if item.cues else item.id)
            retrievability = engine.curve.retrievability(item, day_now)
            reviews += 1
            ok = rng.random() < retrievability
            attempt = item.content if ok else "错误答案"
            result = engine.practice_answer(item.id, attempt, now=day_now)
            if result["success"]:
                successes += 1
            else:
                failures += 1
        for a, b in zip(cats, cats[1:]):
            total_pairs += 1
            if a == b:
                same_cat_pairs += 1
    final_now = now + timedelta(days=14)
    items = engine.store.all_active()
    retrievabilities = [engine.curve.retrievability(i, final_now) for i in items]
    retained = sum(1 for r in retrievabilities if r >= 0.3)
    mean_ret = sum(retrievabilities) / len(items)
    report = {
        "mode": mode,
        "reviews": reviews,
        "successes": successes,
        "failures": failures,
        "same_cat_pairs": same_cat_pairs,
        "total_pairs": total_pairs,
        "same_cat_ratio": round(
            same_cat_pairs / total_pairs, 4
        ) if total_pairs else 0.0,
        "retained": retained,
        "mean_retrievability": round(mean_ret, 3),
    }
    if mode == "none":
        report["baseline_mean"] = round(mean_ret, 3)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "interleave_eval.json"),
    )
    args = parser.parse_args()
    base = _base_engine()
    none_report = _simulate(copy.deepcopy(base), "none", args.seed)
    report = {
        "interleaved": _simulate(copy.deepcopy(base), "interleaved", args.seed),
        "blocked": _simulate(copy.deepcopy(base), "blocked", args.seed),
        "none": none_report,
    }
    baseline = none_report["mean_retrievability"]
    report["interleaved"]["per_review_gain"] = round(
        (report["interleaved"]["mean_retrievability"] - baseline)
        / report["interleaved"]["reviews"],
        5,
    )
    report["blocked"]["per_review_gain"] = round(
        (report["blocked"]["mean_retrievability"] - baseline)
        / report["blocked"]["reviews"],
        5,
    )
    report["all_ok"] = bool(
        report["interleaved"]["same_cat_ratio"]
        < report["blocked"]["same_cat_ratio"]
        and report["interleaved"]["mean_retrievability"]
        >= report["blocked"]["mean_retrievability"] - 0.01
        and report["blocked"]["mean_retrievability"]
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
