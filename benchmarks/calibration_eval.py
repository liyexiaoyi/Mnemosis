"""Metacognitive confidence calibration benchmark.

Measures how well Mnemosis's stated confidence matches its actual retrieval
hit rate (Lichtenstein, Fischhoff & Phillips, 1977; Yeung & Summerfield,
2012):

1. real recall: run the 88 LoCoMo questions; for each top-1 result record the
   predicted confidence and whether it hit;
2. reliability: bucket predictions and compare with empirical hit rates;
3. ECE before vs after blending with per-memory retrieval evidence.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from locomo_bench import generate_dataset

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def run() -> dict:
    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for memory in dataset["facts"] + dataset["events"]:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.8 if memory["kind"] == "semantic" else 0.5,
        )
    rows = []
    for question in dataset["questions"]:
        if question["kind"] == "distractor":
            continue
        results = engine.recall(question["q"], top_k=1)
        if not results:
            rows.append({"q": question["q"], "hit": 0, "pred": None})
            continue
        item = results[0].item
        hit = int(item.content == question["expected"][0])
        pred = engine.confidence(item)[1]
        rows.append({"q": question["q"], "hit": hit, "pred": pred})
    top1_accuracy = round(
        sum(r["hit"] for r in rows) / len(rows), 3
    )

    items = engine.backend.list()
    raw_stats = engine.meta.calibration_stats(items)

    # calibrated ECE: per-item |calibrated_pred - empirical|
    ece_sum = 0.0
    n = 0
    for item in items:
        empirical = engine.meta.calibrate(item)
        if empirical is None:
            continue
        calibrated = engine.meta.calibrated_confidence(item)[1]
        ece_sum += abs(calibrated - empirical)
        n += 1
    calibrated_ece = round(ece_sum / n, 4) if n else None

    # mean predicted vs actual top-1 accuracy (global calibration)
    mean_pred = round(
        sum(r["pred"] for r in rows if r["pred"] is not None)
        / sum(1 for r in rows if r["pred"] is not None),
        3,
    )
    engine.close()
    return {
        "n_questions": len(rows),
        "top1_accuracy": top1_accuracy,
        "mean_predicted_confidence": mean_pred,
        "bias": round(mean_pred - top1_accuracy, 3),
        "ece_raw": raw_stats["ece"],
        "ece_calibrated": calibrated_ece,
        "reliability": raw_stats["buckets"],
        "with_evidence_items": n,
    }


def run_controlled() -> dict:
    """Synthetic memories with 20 retrieval trials each; hit rate correlates
    with strength but with noise, so raw confidence is imperfect."""
    import random

    rng = random.Random(11)
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    items = []
    for i in range(120):
        strength = 0.3 + 0.65 * (i % 4) / 3.0  # 4 strength levels
        true_rate = max(0.05, min(0.98, strength + rng.uniform(-0.15, 0.15)))
        item = engine.remember(
            f"memory {i} is stored.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"cue{i}"],
            importance=0.5,
            strength=strength,
            confidence=0.5 + 0.45 * strength,
        )
        trials = 20
        successes = sum(1 for _ in range(trials) if rng.random() < true_rate)
        item.retrieval_successes = successes
        item.retrieval_failures = trials - successes
        engine.backend.update(item)
        items.append(item)

    raw_stats = engine.meta.calibration_stats(items)
    cal_buckets: dict[int, dict] = {}
    for item in items:
        pred = engine.meta.calibrated_confidence(item)[1]
        bucket = min(4, int(pred * 5))
        entry = cal_buckets.setdefault(
            bucket, {"pred_sum": 0.0, "n": 0, "hits": 0, "fails": 0}
        )
        entry["pred_sum"] += pred
        entry["n"] += 1
        entry["hits"] += item.retrieval_successes
        entry["fails"] += item.retrieval_failures
    reliability_calibrated = []
    for bucket in range(5):
        entry = cal_buckets.get(bucket)
        if not entry or entry["n"] == 0:
            continue
        trials = entry["hits"] + entry["fails"]
        reliability_calibrated.append(
            {
                "predicted_bucket": f"{bucket * 0.2:.1f}-{(bucket + 1) * 0.2:.1f}",
                "n_items": entry["n"],
                "mean_predicted": round(entry["pred_sum"] / entry["n"], 3),
                "empirical_hit_rate": round(
                    (entry["hits"] + 1.0) / (trials + 2.0), 3
                ),
            }
        )
    ece_sum = 0.0
    n = 0
    for item in items:
        empirical = engine.meta.calibrate(item)
        calibrated = engine.meta.calibrated_confidence(item)[1]
        ece_sum += abs(calibrated - empirical)
        n += 1
    engine.close()
    return {
        "n_items": len(items),
        "trials_per_item": 20,
        "ece_raw": raw_stats["ece"],
        "ece_calibrated": round(ece_sum / n, 4),
        "reliability_raw": raw_stats["buckets"],
        "reliability_calibrated": reliability_calibrated,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "calibration_eval.json"
        ),
    )
    args = parser.parse_args()
    report = {"real_locomo": run(), "controlled": run_controlled()}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
