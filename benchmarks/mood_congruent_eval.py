"""Mood-congruent retrieval eval (round 66, Bower 1981).

6 topics, each with a positive memory ("提到红色我喜欢。", affect
=positive) and a negative rival ("提到红色我害怕。", affect=negative).
All parameters are equal and the rival is inserted last (wins ties);
the question's emotion word ("开心") should preferentially retrieve the
matching-affect trace.
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

TOPICS = ["红色", "饺子", "成都", "游泳", "周杰伦", "猫"]


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    now = utcnow() - timedelta(days=10)
    for value in TOPICS:
        engine.remember(
            f"提到{value}我喜欢。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[value],
            affect="positive",
            importance=0.5,
            strength=0.5,
            created_at=now,
        )
        engine.remember(
            f"提到{value}我害怕。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[value],
            affect="negative",
            importance=0.5,
            strength=0.5,
            created_at=now,
        )
    return engine


def _run(boost: bool) -> dict:
    engine = _build_engine()
    hits = 0
    for value in TOPICS:
        results = engine.recall(
            f"为什么提到{value}会开心？",
            top_k=3,
            mood_congruent_boost=boost,
        )
        if "喜欢" in results[0].item.content:
            hits += 1
    return {
        "boost": boost,
        "mood_first": hits,
        "hit_ratio": round(hits / len(TOPICS), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "mood_congruent_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "boosted": _run(True),
        "plain": _run(False),
    }
    report["all_ok"] = bool(
        report["boosted"]["mood_first"] == len(TOPICS)
        and report["boosted"]["mood_first"]
        > report["plain"]["mood_first"]
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
