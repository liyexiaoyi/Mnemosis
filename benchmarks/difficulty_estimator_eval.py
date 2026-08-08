"""Difficulty-estimator eval (round 200, desirable difficulty, Bjork 1994).

10 stores. Each store: 8 memories spread across too-easy / sweet-spot /
hard / very-hard buckets (3/2/2/1), with two hard-very-hard memories
sharing one topic. difficulty_estimator must bucket, summarize and advise.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(3):
        engine.remember(
            f"easy fact {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["easy"],
            importance=0.5,
            strength=0.95,
            auto_cues=False,
        )
    for i, importance in ((0, 0.9), (1, 0.85)):
        engine.remember(
            f"sweet formula {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["数学"],
            importance=importance,
            strength=0.55,
            auto_cues=False,
        )
    engine.remember(
        f"hard concept {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        importance=0.8,
        strength=0.25,
        auto_cues=False,
    )
    engine.remember(
        f"hard concept two {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["化学"],
        importance=0.7,
        strength=0.25,
        auto_cues=False,
    )
    engine.remember(
        f"very hard derivation {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        importance=0.6,
        strength=0.05,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = bucket_ok = ratio_ok = topic_ok = sort_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.difficulty_estimator(limit=10)
        total_ok += int(report["total_memories"] == 8)
        bucket_ok += int(
            report["buckets"]
            == {"too_easy": 3, "sweet_spot": 2, "hard": 2, "very_hard": 1}
        )
        ratio_ok += int(report["sweet_spot_ratio"] == 0.25)
        topic_ok += int(
            any(
                topic["topic"] == "物理"
                and topic["hard"] == 1
                and topic["very_hard"] == 1
                for topic in report["topic_summary"]
            )
        )
        sort_ok += int(
            report["rows"]
            and report["rows"][0]["importance"] == 0.9
            and all(
                report["rows"][i]["importance"]
                >= report["rows"][i + 1]["importance"]
                for i in range(len(report["rows"]) - 1)
            )
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"total_memories", "buckets", "sweet_spot_ratio", "rows",
             "topic_summary", "advice"} <= set(report)
            and all(
                {"id", "preview", "topic", "level", "retrievability",
                 "importance", "reviews"} <= set(row)
                for row in report["rows"]
            )
        )
        via_mcp = server._call_tool("difficulty_estimator", {})
        mcp_ok += int(
            via_mcp["buckets"]["sweet_spot"] == 2
            and via_mcp["buckets"]["very_hard"] == 1
            and via_mcp["sweet_spot_ratio"] == 0.25
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "bucket_ok": bucket_ok,
        "ratio_ok": ratio_ok,
        "topic_ok": topic_ok,
        "sort_ok": sort_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "difficulty_estimator_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(
        v == 10 for k, v in report.items() if k != "stores"
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
