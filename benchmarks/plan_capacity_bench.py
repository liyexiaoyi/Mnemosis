"""Working-memory capacity matching (Miller 1956) at 10k (round 40).

A 5-step reference plan is buried under ~10k noise. With auto capacity
(plan_for_goal top_k=None) the whole plan should surface; a fixed small
top_k=4 truncates mid-plan.
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

from reasoning_zh_10k_bench import generate_memories

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

GOAL = "大壮想去京都旅行，参考阿丽，把完整计划按顺序列出"
STEPS = [
    "阿丽在2026年4月1日订了去京都的机票。",
    "阿丽在2026年4月2日买了相机。",
    "阿丽在2026年4月3日收拾了行李。",
    "阿丽在2026年4月4日订了酒店。",
    "阿丽在2026年4月5日去了京都。",
]


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content in generate_memories():
        cue = content.split("最")[0].split("比")[0].split("买")[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    for i, content in enumerate(STEPS, start=1):
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["阿丽", f"2026-04-0{i}"],
        )
    return engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "plan_capacity_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    report = {"memories": len(engine.store.all_active()), "rows": {}}
    for label, top_k in (("auto", None), ("fixed4", 4)):
        plan = engine.plan_for_goal(
            GOAL, top_k=top_k, outcome_aware=False
        )
        contents = [r.item.content for r in plan]
        coverage = sum(1 for s in STEPS if s in contents)
        report["rows"][label] = {
            "top_k": len(contents),
            "coverage": coverage,
            "ordered": int(
                all(s in contents for s in STEPS)
                and [contents.index(s) for s in STEPS]
                == sorted(contents.index(s) for s in STEPS)
            ),
            "plan": contents,
        }
        print(
            label, "top_k:", len(contents),
            "coverage:", coverage, "/", len(STEPS),
            "ordered:", report["rows"][label]["ordered"],
            flush=True,
        )
    print("memories:", report["memories"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
