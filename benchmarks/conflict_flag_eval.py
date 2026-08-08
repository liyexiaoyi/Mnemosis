"""Conflict-flag eval (round 85, reconsolidation awareness).

8 cue conflicts: a weak-evidence fact (evidence 1, high importance) ranks
first, while a same-cue rival has >= 3x evidence and at least equal source
trust. Recall should flag the top answer as conflicting ("存在更强证据冲
突") and mark it uncertain, so agents do not assert a stale fact.
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
            f"alpha{i} old",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"alpha{i}"],
            importance=0.98,
            strength=0.5,
            evidence_count=1,
            created_at=now,
            auto_cues=False,
        )
        engine.remember(
            f"alpha{i} new",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"alpha{i}"],
            importance=0.5,
            strength=0.5,
            evidence_count=4,
            created_at=now,
            auto_cues=False,
        )
    return engine


def _run(flag: bool) -> dict:
    engine = _build_engine()
    flagged = 0
    for i in range(8):
        results = engine.recall(
            f"alpha{i}",
            top_k=3,
            conflict_flag=flag,
        )
        if (
            not results[0].confident
            and any("更强证据冲突" in r for r in results[0].reasons)
        ):
            flagged += 1
    return {
        "conflict_flag": flag,
        "flagged": flagged,
        "hit_ratio": round(flagged / 8, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "conflict_flag_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "on": _run(True),
        "off": _run(False),
    }
    report["all_ok"] = bool(
        report["on"]["flagged"] == 8
        and report["off"]["flagged"] == 0
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
