"""Source-monitoring eval (round 65, Johnson et al. 1993).

8 conflict pairs sharing one cue: a low-trust memory ("alpha{i} one",
trust 0.4) is inserted last so recency wins ties, and a high-trust memory
("alpha{i} two", trust 1.0) is the correct one. Retrieving the cue should
prefer the trustworthy origin (source monitoring) instead of recency.
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
    for i in range(8):
        cue = f"alpha{i}"
        engine.remember(
            f"{cue} two",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER, trust=1.0),
            cues=[cue],
            importance=0.5,
            strength=0.5,
            auto_cues=False,
        )
        # low-trust rival inserted last -> wins ties by recency
        engine.remember(
            f"{cue} one",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER, trust=0.4),
            cues=[cue],
            importance=0.5,
            strength=0.5,
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
            source_trust_boost=boost,
        )
        if results[0].item.content.endswith("two"):
            wins += 1
    return {
        "boost": boost,
        "winner_first": wins,
        "hit_ratio": round(wins / 8, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "source_monitoring_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "boosted": _run(True),
        "plain": _run(False),
    }
    report["all_ok"] = bool(
        report["boosted"]["winner_first"] == 8
        and report["boosted"]["winner_first"]
        > report["plain"]["winner_first"]
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
