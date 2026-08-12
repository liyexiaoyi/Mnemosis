"""Next-interval eval (round 229, adaptive spacing).

10 stores. Each store: a strong memory (streak 3, 90% accuracy) and a
weak memory (streak 0, ~17% accuracy, important). next_interval must
stretch the strong one and shorten the weak one.
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
    strong = engine.remember(
        f"连对公式 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["数学"],
        importance=0.5,
        strength=0.9,
        auto_cues=False,
    )
    strong.review_streak = 3
    strong.retrieval_successes = 9
    strong.retrieval_failures = 1
    engine.backend.update(strong)
    weak = engine.remember(
        f"总错的单词 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["英语"],
        importance=0.8,
        strength=0.2,
        auto_cues=False,
    )
    weak.review_streak = 0
    weak.retrieval_successes = 1
    weak.retrieval_failures = 5
    engine.backend.update(weak)
    return engine, MCPServer(engine=engine), strong, weak


def _run() -> dict:
    count_ok = order_ok = strong_ok = weak_ok = reason_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server, strong, weak = _store(seed)
        report = engine.next_interval()
        count_ok += int(report["count"] == 2)
        order_ok += int(report["rows"][0]["id"] == strong.id)
        strong_ok += int(
            report["rows"][0]["next_interval_hours"] > 100
            and report["rows"][0]["review_streak"] == 3
        )
        weak_ok += int(report["rows"][1]["next_interval_hours"] < 24)
        reason_ok += int(
            all(row["reason"] for row in report["rows"])
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"count", "rows", "advice"} <= set(report)
            and all(
                {
                    "id",
                    "preview",
                    "review_streak",
                    "accuracy",
                    "retrievability",
                    "next_interval_hours",
                    "reason",
                }
                <= set(row)
                for row in report["rows"]
            )
        )
        via_mcp = server._call_tool(
            "next_interval", {"memory_id": weak.id}
        )
        mcp_ok += int(
            via_mcp["count"] == 1
            and via_mcp["rows"][0]["id"] == weak.id
            and via_mcp["rows"][0]["next_interval_hours"] < 24
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "order_ok": order_ok,
        "strong_ok": strong_ok,
        "weak_ok": weak_ok,
        "reason_ok": reason_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "next_interval_eval.json"),
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
