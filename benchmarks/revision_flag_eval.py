"""Revision-flag eval (round 89, reconsolidation transparency).

8 revised semantic memories (revision_count 1-3 via update) and 8
unrevised ones. Recall should mark revised traces with "已修订(版本n)" so
agents know the fact changed, and leave unrevised traces unmarked.
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
        item = engine.remember(
            f"rev{i} v0",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"rev{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now,
            auto_cues=False,
        )
        for v in range(1, 1 + (i % 3) + 1):
            engine.update(
                item.id, content=f"rev{i} v{v}", now=now
            )
        engine.remember(
            f"plain{i} fact",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"plain{i}"],
            importance=0.5,
            strength=0.5,
            created_at=now,
            auto_cues=False,
        )
    return engine


def _run(flag: bool) -> dict:
    engine = _build_engine()
    revised_flagged = 0
    plain_flagged = 0
    for i in range(8):
        res = engine.recall(f"rev{i}", top_k=3, revision_flag=flag)
        revised_flagged += int(
            any("已修订" in r for r in res[0].reasons)
        )
        res2 = engine.recall(
            f"plain{i}", top_k=3, revision_flag=flag
        )
        plain_flagged += int(
            any("已修订" in r for r in res2[0].reasons)
        )
    return {
        "revision_flag": flag,
        "revised_flagged": revised_flagged,
        "plain_flagged": plain_flagged,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "revision_flag_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "on": _run(True),
        "off": _run(False),
    }
    report["all_ok"] = bool(
        report["on"]["revised_flagged"] == 8
        and report["on"]["plain_flagged"] == 0
        and report["off"]["revised_flagged"] == 0
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
