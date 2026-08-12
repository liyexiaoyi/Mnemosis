"""Reconsolidation-plan eval (round 223, memory update).

10 stores. Each store: two conflicting date facts. reconsolidation_plan
must find the target, gather the conflict and return retrieve -> update
-> reconsolidate steps; a missing id must return found=False.
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
    a = engine.remember(
        f"会议在周一 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["日期"],
        confidence=0.9,
        auto_cues=False,
    )
    engine.remember(
        f"会议在周二 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["日期"],
        confidence=0.9,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine), a


def _run() -> dict:
    found_ok = mem_ok = conflict_ok = step_ok = advice_ok = fields_ok = (
        mcp_ok
    ) = missing_ok = 0
    for seed in range(10):
        engine, server, a = _store(seed)
        report = engine.reconsolidation_plan(a.id)
        found_ok += int(report["found"] is True)
        mem_ok += int(
            report["memory"]["id"] == a.id
            and {"id", "preview", "confidence", "evidence_count",
                 "revision_count", "retrievability"}
            <= set(report["memory"])
        )
        conflict_ok += int(len(report["conflicts"]) >= 1)
        step_ok += int(
            [step["order"] for step in report["steps"]] == [1, 2, 3, 4]
            and all(
                step["verdict"] in ("ok", "weak")
                for step in report["steps"]
            )
        )
        advice_ok += int("冲突" in report["advice"])
        fields_ok += int(
            {
                "found",
                "memory",
                "related_count",
                "conflicts",
                "steps",
                "advice",
            }
            <= set(report)
            and all(
                {"id", "preview", "confidence"} <= set(conflict)
                for conflict in report["conflicts"]
            )
        )
        missing_ok += int(
            engine.reconsolidation_plan("no-such-id")["found"] is False
        )
        via_mcp = server._call_tool(
            "reconsolidation_plan", {"memory_id": a.id}
        )
        mcp_ok += int(
            via_mcp["found"] is True
            and len(via_mcp["conflicts"]) >= 1
        )
    return {
        "stores": 10,
        "found_ok": found_ok,
        "mem_ok": mem_ok,
        "conflict_ok": conflict_ok,
        "step_ok": step_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
        "missing_ok": missing_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "reconsolidation_plan_eval.json"),
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
