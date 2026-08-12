"""Plan depth adaptation (resource-rational planning, round 42).

Simple goals -> shallow fast plan (6 items, no outcome rerank); goals with
references -> medium (8, rerank); goals with many references + constraints
-> deep plan (14, rerank). Verifies auto effort mapping and plan behavior.
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

GOALS = [
    {"goal": "大壮想去京都旅行", "expected_effort": "low",
     "expected_top_k": 6, "rerank": False},
    {"goal": "大壮想去京都旅行，参考阿丽", "expected_effort": "medium",
     "expected_top_k": 8, "rerank": True},
    {
        "goal": "大壮想去京都旅行，参考阿丽和小波，预算5000，3个人，按顺序列出",
        "expected_effort": "high",
        "expected_top_k": 14,
        "rerank": True,
    },
]


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content, person, iso in (
        ("阿丽在2026年4月1日订了去京都的机票。", "阿丽", "2026-04-01"),
        ("阿丽在2026年4月2日买了相机。", "阿丽", "2026-04-02"),
        ("小波在2026年5月1日订了去京都的机票。", "小波", "2026-05-01"),
        ("小波在2026年5月2日买了相机。", "小波", "2026-05-02"),
    ):
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, iso],
        )
    engine.record_outcome("阿丽旅行", "订机票", success=False, note="航班取消")
    engine.record_outcome("阿丽旅行", "订机票", success=False, note="再次取消")
    engine.record_outcome("小波旅行", "订机票", success=True)
    engine.record_outcome("小波旅行", "买相机", success=True)
    # filler episodic memories so capacity is actually observable
    for i in range(12):
        day = 10 + i
        engine.remember(
            f"大壮在2025年{i+1}月{day % 28 + 1}日去了京都附近的"
            f"城市{i + 1}。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["大壮", f"2025-{i+1:02d}-{day % 28 + 1:02d}"],
        )
    return engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "plan_effort_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    report = {"rows": []}
    all_ok = True
    for g in GOALS:
        effort = engine._plan_effort(g["goal"])
        plan = engine.plan_for_goal(g["goal"])
        contents = [r.item.content for r in plan]
        reranked = any(
            "\u7ed3\u679c\u52a0\u6743" in reason
            for r in plan
            for reason in r.reasons
        )
        ok = (
            effort == g["expected_effort"]
            and len(contents) == g["expected_top_k"]
            and reranked == g["rerank"]
        )
        all_ok = all_ok and ok
        report["rows"].append(
            {
                "goal": g["goal"],
                "effort": effort,
                "expected_effort": g["expected_effort"],
                "top_k": len(contents),
                "expected_top_k": g["expected_top_k"],
                "reranked": reranked,
                "expected_rerank": g["rerank"],
                "ok": ok,
            }
        )
        print(
            g["goal"][:22], "effort:", effort, "top_k:", len(contents),
            "rerank:", reranked, "ok:", ok,
            flush=True,
        )
    report["all_ok"] = all_ok
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
