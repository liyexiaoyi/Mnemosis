"""Constructivist accommodation benchmark (Piaget; CAM, Li et al. 2025).

When new information strongly out-evidence an old fact that shares its schema
(cue), sleep should *accommodate*: retire the stale fact and keep the new one.
Balanced disagreements (equal evidence) must NOT be accommodated -- they stay
as detected contradictions for the agent to resolve.
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


def _run_pair(seed: int, lopsided: bool) -> dict:
    engine = MemoryEngine()
    old_trust = SourceRecord(origin=SourceType.USER, trust=0.8)
    new_trust = SourceRecord(origin=SourceType.USER, trust=0.9)
    cue = f"topic{seed}"
    old_content = f"{cue} has value alpha."
    new_content = f"{cue} has value beta."
    engine.remember(
        old_content,
        kind=MemoryKind.SEMANTIC,
        source=old_trust,
        cues=[cue],
        evidence_count=1,
    )
    engine.remember(
        new_content,
        kind=MemoryKind.SEMANTIC,
        source=new_trust,
        cues=[cue],
        evidence_count=4 if lopsided else 1,
    )
    report = engine.sleep()
    active = engine.backend.list(kind=MemoryKind.SEMANTIC)
    active_content = {i.content for i in active}
    stale_retired = old_content not in active_content
    new_kept = new_content in active_content
    top1 = engine.recall(cue, top_k=1)
    conflicts_after = len(engine.consolidator.detect_conflicts())
    engine.close()
    return {
        "lopsided": lopsided,
        "stale_retired": stale_retired,
        "new_kept": new_kept,
        "new_top1": bool(top1) and top1[0].item.content == new_content,
        "conflicts_after": conflicts_after,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=20)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "accommodation_eval.json"
        ),
    )
    args = parser.parse_args()
    lopsided = [_run_pair(i, True) for i in range(args.trials)]
    balanced = [_run_pair(i, False) for i in range(args.trials)]
    report = {
        "trials": args.trials,
        "lopsided_evidence": {
            "stale_retired": sum(r["stale_retired"] for r in lopsided),
            "new_kept": sum(r["new_kept"] for r in lopsided),
            "new_top1_recall": sum(r["new_top1"] for r in lopsided),
            "conflicts_after_sum": sum(r["conflicts_after"] for r in lopsided),
        },
        "balanced_control": {
            "stale_retired": sum(r["stale_retired"] for r in balanced),
            "new_top1_recall": sum(r["new_top1"] for r in balanced),
            "conflicts_after_sum": sum(r["conflicts_after"] for r in balanced),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
