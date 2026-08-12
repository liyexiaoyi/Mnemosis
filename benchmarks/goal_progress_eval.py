"""Goal-progress eval (round 240, self-regulated learning).

10 stores. Each store: a developing physics topic. goal_progress must
map the goal to physics, report in_progress and handle unknown goals.
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
        item = engine.remember(
            f"物理题 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            confidence=0.5,
            strength=0.5,
            auto_cues=False,
        )
        item.retrieval_successes = 5
        item.retrieval_failures = 5
        engine.backend.update(item)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    goal_ok = matched_ok = status_ok = ratio_ok = advice_ok = missing_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.goal_progress("物理")
        goal_ok += int(report["goal"] == "物理")
        matched_ok += int(report["matched_topic"] == "物理")
        status_ok += int(report["status"] == "in_progress")
        ratio_ok += int(0 < report["progress_ratio"] <= 1)
        advice_ok += int("下一步" in report["advice"])
        missing = engine.goal_progress("航天")
        missing_ok += int(
            missing["status"] == "not_started"
            and missing["matched_topic"] is None
            and missing["progress_ratio"] == 0.0
        )
        fields_ok += int(
            {"goal", "matched_topic", "progress_ratio", "status", "advice"}
            <= set(report)
        )
        via_mcp = server._call_tool("goal_progress", {"goal": "物理"})
        mcp_ok += int(
            via_mcp["matched_topic"] == "物理"
            and via_mcp["status"] == "in_progress"
        )
    return {
        "stores": 10,
        "goal_ok": goal_ok,
        "matched_ok": matched_ok,
        "status_ok": status_ok,
        "ratio_ok": ratio_ok,
        "advice_ok": advice_ok,
        "missing_ok": missing_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "goal_progress_eval.json"),
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
