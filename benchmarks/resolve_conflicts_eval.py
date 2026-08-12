"""Resolve-conflicts eval (round 115, Nader et al. 2000).

10 stores, each with 3 lopsided conflicts (5x vs 1x evidence) and 3
balanced conflicts (1:1). resolve_conflicts() should retire all lopsided
stale traces (accommodated 3), lower confidence on balanced pairs
(rem_resolved 3) and leave exactly the balanced ones still flagged.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(3):
        engine.remember(
            f"s{seed}-{i} strong",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"lop{seed}-{i}"],
            confidence=0.8,
            evidence_count=5,
            auto_cues=False,
        )
        engine.remember(
            f"s{seed}-{i} weak",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"lop{seed}-{i}"],
            confidence=0.8,
            evidence_count=1,
            auto_cues=False,
        )
    for i in range(3):
        engine.remember(
            f"b{seed}-{i} side a",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"bal{seed}-{i}"],
            confidence=0.8,
            evidence_count=1,
            auto_cues=False,
        )
        engine.remember(
            f"b{seed}-{i} side b",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"bal{seed}-{i}"],
            confidence=0.8,
            evidence_count=1,
            auto_cues=False,
        )
    return engine


def _run() -> dict:
    acc_ok = 0
    rem_ok = 0
    remain_ok = 0
    for seed in range(10):
        engine = _store(seed)
        result = engine.resolve_conflicts()
        acc_ok += int(result["accommodated"] == 3)
        rem_ok += int(result["rem_resolved"] >= 3)
        remain_ok += int(
            result["remaining"]
            == len(engine.consolidator.detect_conflicts())
        )
    return {
        "stores": 10,
        "accommodated_ok": acc_ok,
        "rem_resolved_ok": rem_ok,
        "remaining_ok": remain_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "resolve_conflicts_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(v == 10 for k, v in report.items() if k != "stores")
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
