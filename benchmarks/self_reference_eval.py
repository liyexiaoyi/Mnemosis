"""Self-reference effect eval (round 64, Rogers et al. 1977).

6 topics, each with a self-related memory ("我喜欢红色。") and a rival
memory about someone else ("小明喜欢红色。"). The rival is deliberately
more salient (importance 0.8 vs 0.5) so it wins without the mechanism;
the self-reference cue in the question ("我喜欢的...") should tip the
ranking back to the self-related trace.
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

TOPICS = [
    ("颜色", "红色"),
    ("食物", "饺子"),
    ("城市", "成都"),
    ("运动", "游泳"),
    ("歌手", "周杰伦"),
    ("动物", "猫"),
]


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for _, value in TOPICS:
        engine.remember(
            f"我喜欢{value}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[value],
            importance=0.5,
            strength=0.5,
        )
        engine.remember(
            f"小明喜欢{value}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[value],
            importance=0.8,
            strength=0.5,
        )
    return engine


def _run(boost: bool) -> dict:
    engine = _build_engine()
    hits = 0
    ranks = []
    for topic, value in TOPICS:
        results = engine.recall(
            f"我喜欢的{topic}是什么？",
            top_k=3,
            self_reference_boost=boost,
        )
        for i, res in enumerate(results, start=1):
            if res.item.content.startswith("我喜欢"):
                ranks.append(i)
                break
        top_content = results[0].item.content
        if top_content.startswith("我喜欢"):
            hits += 1
    return {
        "boost": boost,
        "self_first": hits,
        "hit_ratio": round(hits / len(TOPICS), 3),
        "avg_rank": round(sum(ranks) / len(ranks), 3) if ranks else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "self_reference_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "boosted": _run(True),
        "plain": _run(False),
    }
    report["all_ok"] = bool(
        report["boosted"]["self_first"] > report["plain"]["self_first"]
        and report["boosted"]["self_first"] == len(TOPICS)
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
