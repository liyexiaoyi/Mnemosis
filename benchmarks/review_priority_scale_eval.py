"""Review-priority scale eval: does importance-first protect salient memories
when the daily review quota is scarce at 10k scale?

100 high-importance + 9,900 low-importance memories, all 60 days old. For 30
days the scheduler gets only 20 review slots per day. We measure how many
high- vs low-importance memories remain strongly retrievable afterwards,
comparing importance-first vs most-forgotten-first scheduling.
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

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def run(
    n_high: int = 100,
    n_low: int = 9900,
    days: int = 30,
    daily_limit: int = 20,
    importance_first: bool = True,
) -> dict:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(n_high):
        engine.remember(
            f"important memory {i} is true.",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"imp{i}"],
            importance=0.9,
            created_at=now - timedelta(days=60),
        )
    for i in range(n_low):
        engine.remember(
            f"minor memory {i}.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"low{i}"],
            importance=0.3,
            created_at=now - timedelta(days=60),
        )
    reviewed = 0
    for day_offset in range(days):
        day = now + timedelta(days=day_offset)
        for item in engine.review_due(
            limit=daily_limit,
            now=day,
            importance_first=importance_first,
        ):
            engine.review(item.id, success=True, now=day)
            reviewed += 1
    final = now + timedelta(days=days)
    high_kept = 0
    low_kept = 0
    for item in engine.backend.list():
        if engine.curve.retrievability(item, final) > 0.3:
            if item.importance >= 0.7:
                high_kept += 1
            else:
                low_kept += 1
    engine.close()
    return {
        "importance_first": importance_first,
        "n_high": n_high,
        "n_low": n_low,
        "reviews_done": reviewed,
        "high_kept_strong": high_kept,
        "low_kept_strong": low_kept,
        "high_kept_ratio": round(high_kept / n_high, 3),
        "low_kept_ratio": round(low_kept / n_low, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n-high", type=int, default=100)
    parser.add_argument("--n-low", type=int, default=9900)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--daily-limit", type=int, default=20)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "review_priority_scale.json"
        ),
    )
    args = parser.parse_args()
    on = run(args.n_high, args.n_low, args.days, args.daily_limit, True)
    off = run(args.n_high, args.n_low, args.days, args.daily_limit, False)
    report = {"on": on, "off": off}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
