"""Cramming-plan eval (round 160, Cepeda et al. 2006).

10 stores. Each store: 6 memories (3 high-importance + 3 low). With 2
hours before a deadline, cramming_plan must split into 4 short sessions,
cover all 6 memories and put high-priority ones first.
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
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, list[str]]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    high_ids = []
    for i in range(3):
        item = engine.remember(
            f"zzz high {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"ch-{seed}-{i}"],
            importance=0.9,
            auto_cues=False,
        )
        high_ids.append(item.id)
    for i in range(3):
        engine.remember(
            f"zzz low {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"cl-{seed}-{i}"],
            importance=0.3,
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine), high_ids


def _run() -> dict:
    total_ok = sessions_ok = counts_ok = priority_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, high_ids = _store(seed)
        target = utcnow() + timedelta(hours=3)
        plan = engine.cramming_plan(
            target_at=target,
            hours_available=2.0,
            session_minutes=30,
            limit=6,
        )
        total_ok += int(plan["total_memories"] == 6)
        sessions_ok += int(len(plan["sessions"]) == 4)
        counts_ok += int(
            sum(s["count"] for s in plan["sessions"]) == 6
            and all(s["count"] >= 1 for s in plan["sessions"])
        )
        first_ids = set(plan["sessions"][0]["memory_ids"])
        priority_ok += int(bool(first_ids & set(high_ids)))
        fields_ok += int(
            {"target_at", "hours_available", "sessions",
             "total_memories"} <= set(plan)
            and all(
                {"start_at", "duration_minutes", "memory_ids", "count"}
                <= set(s)
                for s in plan["sessions"]
            )
        )
        via_mcp = server._call_tool(
            "cramming_plan",
            {"target_at": target.isoformat(), "hours_available": 2},
        )
        mcp_ok += int(
            via_mcp["total_memories"] == 6
            and len(via_mcp["sessions"]) == 4
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "sessions_ok": sessions_ok,
        "counts_ok": counts_ok,
        "priority_ok": priority_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "cramming_plan_eval.json"),
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
