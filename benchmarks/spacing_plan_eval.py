"""Spacing-plan eval (round 214, distributed practice).

10 stores. Each store: 6 memories with different strengths/importances.
spacing_plan must spread them over days, put the most important first in
each day, and interleave topics.
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
from mnemosis.mcp_server import MCPServer
from mnemosis.types import (
    MemoryKind,
    SourceRecord,
    SourceType,
    utcnow,
)


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    plan = [
        (f"甲-1 {seed}", "甲", 0.20, 0.7),
        (f"甲-2 {seed}", "甲", 0.30, 0.9),
        (f"甲-3 {seed}", "甲", 0.40, 0.8),
        (f"乙-1 {seed}", "乙", 0.35, 0.7),
        (f"乙-2 {seed}", "乙", 0.55, 0.7),
        (f"丙-1 {seed}", "丙", 0.95, 0.7),
    ]
    for content, cue, strength, importance in plan:
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[cue],
            importance=importance,
            strength=strength,
            created_at=now - timedelta(days=1),
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = day_ok = order_ok = interleave_ok = span_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.spacing_plan(days=7, limit=10)
        total_ok += int(report["total_scheduled"] == 6)
        populated = [
            day["day"] for day in report["daily_plan"] if day["items"]
        ]
        day_ok += int(populated == [1, 2, 3, 5])
        order_seed_ok = True
        for day in report["daily_plan"]:
            if not day["items"]:
                continue
            imps = [item["importance"] for item in day["items"]]
            if imps[0] != max(imps):
                order_seed_ok = False
        order_ok += int(order_seed_ok)
        interleave_seed_ok = True
        for day in report["daily_plan"]:
            topics = []
            for item in day["items"]:
                stored = engine.backend.get(item["id"])
                topics.append(stored.cues[0])
            if not all(
                topics[i] != topics[i + 1]
                for i in range(len(topics) - 1)
            ):
                interleave_seed_ok = False
        interleave_ok += int(interleave_seed_ok)
        span_ok += int(
            min(populated) < max(populated) and len(populated) == 4
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"days", "total_scheduled", "daily_plan", "advice"} <= set(report)
            and all(
                {"day", "items"} <= set(day)
                for day in report["daily_plan"]
            )
            and all(
                {"id", "preview", "importance", "retrievability"}
                <= set(item)
                for day in report["daily_plan"]
                for item in day["items"]
            )
        )
        via_mcp = server._call_tool(
            "spacing_plan", {"days": 7, "limit": 10}
        )
        mcp_ok += int(
            via_mcp["total_scheduled"] == 6
            and len(via_mcp["daily_plan"]) == 7
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "day_ok": day_ok,
        "order_ok": order_ok,
        "interleave_ok": interleave_ok,
        "span_ok": span_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "spacing_plan_eval.json"),
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
