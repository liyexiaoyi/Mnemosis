"""Decay-flag eval (round 94, Ebbinghaus forgetting curve).

8 weak memories (strength 0.3, 40 days old - retrievability below 0.3)
and 8 strong memories (0.9, 1 day). Recall should mark the weak ones
"低可提取(快遗忘)" and leave strong ones unmarked.
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
    now = utcnow()
    for i in range(8):
        engine.remember(
            f"weak{i} fading",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"weak{i}"],
            importance=0.5,
            strength=0.3,
            created_at=now - timedelta(days=40),
            auto_cues=False,
        )
        engine.remember(
            f"strong{i} fresh",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"strong{i}"],
            importance=0.5,
            strength=0.9,
            created_at=now - timedelta(days=1),
            auto_cues=False,
        )
    return engine


def _run(flag: bool) -> dict:
    engine = _build_engine()
    weak_flagged = 0
    strong_flagged = 0
    for i in range(8):
        res = engine.recall(f"weak{i}", top_k=3, decay_flag=flag)
        weak_flagged += int(
            any("快遗忘" in r for r in res[0].reasons)
        )
        res2 = engine.recall(
            f"strong{i}", top_k=3, decay_flag=flag
        )
        strong_flagged += int(
            any("快遗忘" in r for r in res2[0].reasons)
        )
    return {
        "decay_flag": flag,
        "weak_flagged": weak_flagged,
        "strong_flagged": strong_flagged,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "decay_flag_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "on": _run(True),
        "off": _run(False),
    }
    report["all_ok"] = bool(
        report["on"]["weak_flagged"] == 8
        and report["on"]["strong_flagged"] == 0
        and report["off"]["weak_flagged"] == 0
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
