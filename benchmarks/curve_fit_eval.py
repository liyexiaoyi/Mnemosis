"""Curve-fit eval (round 238, individual forgetting rates).

10 stores. Each store: a fast-forgetting memory (1/6 success) and a
well-consolidated memory (10/10 success). curve_fit must estimate slower
decay for the consolidated one and predict a longer time to threshold.
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
    fast = engine.remember(
        f"易忘内容 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["易忘"],
        strength=0.9,
        auto_cues=False,
    )
    fast.retrieval_successes = 1
    fast.retrieval_failures = 5
    engine.backend.update(fast)
    slow = engine.remember(
        f"巩固内容 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["巩固"],
        strength=0.9,
        auto_cues=False,
    )
    slow.retrieval_successes = 10
    slow.retrieval_failures = 0
    engine.backend.update(slow)
    return engine, MCPServer(engine=engine), fast, slow


def _run() -> dict:
    count_ok = order_ok = fast_ok = slow_ok = reason_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server, fast, slow = _store(seed)
        report = engine.curve_fit(horizon_days=30, threshold=0.4)
        count_ok += int(report["count"] == 2)
        order_ok += int(report["rows"][0]["id"] == fast.id)
        fast_ok += int(
            report["rows"][0]["days_to_threshold"] > 0
            and report["rows"][0]["success_rate"] == round(1 / 6, 3)
        )
        slow_ok += int(
            report["rows"][1]["days_to_threshold"]
            > report["rows"][0]["days_to_threshold"]
            and report["rows"][1]["success_rate"] == 1.0
        )
        reason_ok += int(all(row["reason"] for row in report["rows"]))
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"count", "threshold", "rows", "advice"} <= set(report)
            and all(
                {
                    "id",
                    "preview",
                    "retrievability",
                    "attempts",
                    "success_rate",
                    "estimated_rate_per_hour",
                    "days_to_threshold",
                    "reason",
                }
                <= set(row)
                for row in report["rows"]
            )
        )
        via_mcp = server._call_tool(
            "curve_fit", {"memory_id": slow.id, "threshold": 0.4}
        )
        mcp_ok += int(
            via_mcp["count"] == 1
            and via_mcp["rows"][0]["id"] == slow.id
            and via_mcp["rows"][0]["days_to_threshold"] > 0
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "order_ok": order_ok,
        "fast_ok": fast_ok,
        "slow_ok": slow_ok,
        "reason_ok": reason_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "curve_fit_eval.json"),
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
