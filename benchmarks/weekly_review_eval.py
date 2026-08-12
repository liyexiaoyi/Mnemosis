"""Weekly-review eval (round 234, aggregated health report).

10 stores. Each store: two unreviewed physics memories, an overconfident
math memory and an underconfident English memory. weekly_review must
report counts, blind spots, risk, calibration and a plan.
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
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(2):
        engine.remember(
            f"物理盲区 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.7,
            auto_cues=False,
        )
    math = engine.remember(
        f"数学题 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["数学"],
        confidence=0.95,
        auto_cues=False,
    )
    math.retrieval_successes = 7
    math.retrieval_failures = 3
    engine.backend.update(math)
    eng = engine.remember(
        f"英语单词 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["英语"],
        confidence=0.5,
        auto_cues=False,
    )
    eng.retrieval_successes = 9
    eng.retrieval_failures = 1
    engine.backend.update(eng)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = topic_ok = weak_ok = risk_ok = calib_ok = plan_ok = (
        advice_ok
    ) = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.weekly_review()
        summary = report["week_summary"]
        total_ok += int(summary["total_memories"] == 4)
        topic_ok += int(summary["topics"] >= 1)
        weak_ok += int(
            any(
                topic["topic"] == "物理" and topic["status"] == "unreviewed"
                for topic in summary["weak_topics"]
            )
        )
        risk_ok += int(len(summary["riskiest_ids"]) >= 1)
        calib_ok += int(0 <= summary["calibration_score"] <= 1)
        plan_ok += int(len(report["next_week_plan"]) == 4)
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"week_summary", "next_week_plan", "advice"} <= set(report)
            and {
                "total_memories",
                "topics",
                "weak_topics",
                "avg_risk",
                "riskiest_ids",
                "calibration_score",
                "tonight_candidates",
            }
            <= set(summary)
        )
        via_mcp = server._call_tool("weekly_review", {})
        mcp_ok += int(
            via_mcp["week_summary"]["total_memories"] == 4
            and len(via_mcp["next_week_plan"]) >= 1
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "topic_ok": topic_ok,
        "weak_ok": weak_ok,
        "risk_ok": risk_ok,
        "calib_ok": calib_ok,
        "plan_ok": plan_ok,
        "advice_ok": advice_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "weekly_review_eval.json"),
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
