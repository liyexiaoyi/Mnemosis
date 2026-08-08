"""Weak-important sleep replay eval (round 77, Stickgold & Walker 2013).

30 semantic memories, all weak (strength 0.3, 60 days old): 15 important
(importance 0.8) + 15 unimportant (0.3). Sleep should replay the
important-but-fading traces (bounded), protecting them from silent
forgetting, while leaving unimportant ones mostly alone.
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


def _base_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(15):
        engine.remember(
            f"重要记忆{i}：关键事实{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"重要{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=60),
        )
        engine.remember(
            f"琐碎记忆{i}：普通记录{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"琐碎{i}"],
            importance=0.3,
            strength=0.3,
            created_at=now - timedelta(days=60),
        )
    return engine


def _run(sleep: bool) -> dict:
    engine = _base_engine()
    now = utcnow()
    weak_replayed = 0
    if sleep:
        report = engine.sleep(now=now)
        weak_replayed = report.weak_replayed
    high = []
    low = []
    for item in engine.store.all_active():
        r = engine.curve.retrievability(item, now)
        if item.importance >= 0.7:
            high.append(r)
        else:
            low.append(r)
    return {
        "sleep": sleep,
        "weak_replayed": weak_replayed,
        "important_mean": round(sum(high) / len(high), 4),
        "trivial_mean": round(sum(low) / len(low), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "weak_important_replay_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "sleep": _run(True),
        "no_sleep": _run(False),
    }
    report["all_ok"] = bool(
        report["sleep"]["weak_replayed"] > 0
        and report["sleep"]["important_mean"]
        > report["no_sleep"]["important_mean"]
        and (
            report["sleep"]["important_mean"]
            - report["no_sleep"]["important_mean"]
        )
        > (
            report["sleep"]["trivial_mean"]
            - report["no_sleep"]["trivial_mean"]
        )
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
