"""Emotional salience eval (round 79, Kensinger 2009).

8 topics, each with an emotional trace ("记录i甲很紧张。", affect
=negative) and a neutral trace ("记录i乙很普通。", affect=None, slightly
more important 0.7 vs 0.5 so it wins ties without the mechanism). Each
pair has a unique cue ("tagi"). The emotional trace should still rank
first because emotional content is prioritized in memory.
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


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    now = utcnow() - timedelta(days=10)
    for i in range(8):
        engine.remember(
            f"记录{i}乙很普通。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"tag{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now,
        )
        engine.remember(
            f"记录{i}甲很紧张。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"tag{i}"],
            affect="negative",
            importance=0.5,
            strength=0.5,
            created_at=now,
        )
    return engine


def _run(boost: bool) -> dict:
    engine = _build_engine()
    hits = 0
    for i in range(8):
        results = engine.recall(
            f"tag{i}",
            top_k=3,
            emotional_salience_boost=boost,
        )
        if results[0].item.content == f"记录{i}甲很紧张。":
            hits += 1
    return {
        "boost": boost,
        "emotional_first": hits,
        "hit_ratio": round(hits / 8, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "emotional_salience_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "boosted": _run(True),
        "plain": _run(False),
    }
    report["all_ok"] = bool(
        report["boosted"]["emotional_first"] == 8
        and report["boosted"]["emotional_first"]
        > report["plain"]["emotional_first"]
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
