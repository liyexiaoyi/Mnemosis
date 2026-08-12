"""Confidence-weighted recall eval (round 67, Koriat & Goldsmith 1996).

8 cue conflicts: a high-confidence memory ("alpha{i} two", confidence
0.9) is inserted first, a low-confidence rival ("alpha{i} one",
confidence 0.4) is inserted last so recency wins ties. Retrieval should
prefer the memory the system itself is confident about (metacognitive
calibration) instead of the more recent trace.
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

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for i in range(8):
        cue = f"alpha{i}"
        engine.remember(
            f"{cue} two",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.5,
            strength=0.5,
            confidence=0.9,
            auto_cues=False,
        )
        engine.remember(
            f"{cue} one",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.5,
            strength=0.5,
            confidence=0.4,
            auto_cues=False,
        )
    return engine


def _run(boost: bool) -> dict:
    engine = _build_engine()
    wins = 0
    for i in range(8):
        results = engine.recall(
            f"alpha{i}",
            top_k=3,
            confidence_boost=boost,
        )
        if results[0].item.content.endswith("two"):
            wins += 1
    return {
        "boost": boost,
        "confident_first": wins,
        "hit_ratio": round(wins / 8, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "confidence_weighted_eval.json"
        ),
    )
    args = parser.parse_args()
    report = {
        "boosted": _run(True),
        "plain": _run(False),
    }
    report["all_ok"] = bool(
        report["boosted"]["confident_first"] == 8
        and report["boosted"]["confident_first"]
        > report["plain"]["confident_first"]
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
