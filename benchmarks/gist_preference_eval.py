"""Gist-preference eval (round 76, Brainerd & Reyna 1990).

8 topics, each with an old consolidated gist (semantic, 60 days old:
"要点：阿丽喜欢红色。") and a recent verbatim detail (episodic, 2 days
old: "阿丽说：我最喜欢红色。"). Summary questions ("总结一下...") should
prefer the gist even though the verbatim trace is much fresher.
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

TOPICS = [
    ("颜色", "红色"),
    ("食物", "饺子"),
    ("城市", "成都"),
    ("运动", "游泳"),
    ("歌手", "周杰伦"),
    ("动物", "猫"),
    ("季节", "春天"),
    ("电影", "科幻片"),
]


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for _, value in TOPICS:
        engine.remember(
            f"要点：阿丽喜欢{value}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[value],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=60),
        )
        engine.remember(
            f"阿丽说：我最喜欢{value}。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[value],
            importance=0.5,
            strength=0.5,
            created_at=now - timedelta(days=2),
        )
    return engine


def _run(gist_preference: bool) -> dict:
    engine = _build_engine()
    hits = 0
    for topic, _ in TOPICS:
        results = engine.recall(
            f"总结一下阿丽喜欢什么{topic}？",
            top_k=3,
            gist_preference=gist_preference,
        )
        if "要点" in results[0].item.content:
            hits += 1
    return {
        "gist_preference": gist_preference,
        "gist_first": hits,
        "hit_ratio": round(hits / len(TOPICS), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "gist_preference_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "boosted": _run(True),
        "plain": _run(False),
    }
    report["all_ok"] = bool(
        report["boosted"]["gist_first"] == len(TOPICS)
        and report["boosted"]["gist_first"]
        > report["plain"]["gist_first"]
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
