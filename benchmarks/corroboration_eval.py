"""Corroboration eval (round 86, Johnson et al. 1993 source monitoring).

8 cue conflicts: a single-confirmation fact (evidence 1, higher
importance 0.77) edges out a multi-confirmed fact (evidence 3, importance
0.5) by a small margin. The corroboration boost should put the
multi-confirmed trace first because it was confirmed by several sources.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow() - timedelta(days=10)
    for i in range(8):
        engine.remember(
            f"alpha{i} single",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"alpha{i}"],
            importance=0.77,
            strength=0.5,
            evidence_count=1,
            created_at=now,
            auto_cues=False,
        )
        engine.remember(
            f"alpha{i} confirmed",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"alpha{i}"],
            importance=0.5,
            strength=0.5,
            evidence_count=3,
            created_at=now,
            auto_cues=False,
        )
    return engine


def _run(boost: bool) -> dict:
    engine = _build_engine()
    hits = 0
    for i in range(8):
        results = engine.recall(
            f"alpha{i}",
            top_k=3,
            corroboration_boost=boost,
        )
        if results[0].item.content.endswith("confirmed"):
            hits += 1
    return {
        "boost": boost,
        "confirmed_first": hits,
        "hit_ratio": round(hits / 8, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "corroboration_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "boosted": _run(True),
        "plain": _run(False),
    }
    report["all_ok"] = bool(
        report["boosted"]["confirmed_first"] == 8
        and report["plain"]["confirmed_first"] == 0
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
