"""Intent-conflicts eval (round 141, Einstein & McDaniel 1990).

10 stores. Each store registers 5 intentions: two due 10 minutes apart,
one far away, and two sharing a context cue. intent_conflicts must report
exactly the time clash and the context clash.
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
from mnemosis.types import utcnow  # noqa: E402


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str]:
    engine = MemoryEngine()
    now = utcnow()
    i1 = engine.remember_intent(
        f"call a {seed}", due_at=now + timedelta(minutes=10)
    )
    i2 = engine.remember_intent(
        f"call b {seed}", due_at=now + timedelta(minutes=20)
    )
    i3 = engine.remember_intent(
        f"later {seed}", due_at=now + timedelta(hours=2)
    )
    engine.remember_intent(
        f"office a {seed}", due_at=now + timedelta(days=1),
        context_cue="office",
    )
    engine.remember_intent(
        f"office b {seed}", due_at=now + timedelta(days=2),
        context_cue="office",
    )
    return engine, MCPServer(engine=engine), i3["id"]


def _run() -> dict:
    time_ok = gap_ok = context_ok = no_ok = total_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, i3id = _store(seed)
        result = engine.intent_conflicts(time_window_minutes=60)
        time_hits = [c for c in result["conflicts"] if c["type"] == "time"]
        context_hits = [
            c for c in result["conflicts"] if c["type"] == "context"
        ]
        time_ok += int(len(time_hits) == 1)
        gap_ok += int(time_hits and time_hits[0]["gap_minutes"] == 10.0)
        context_ok += int(
            len(context_hits) == 1 and context_hits[0]["cue"] == "office"
        )
        involved = {
            c["intent_a"] for c in result["conflicts"]
        } | {c["intent_b"] for c in result["conflicts"]}
        no_ok += int(i3id not in involved)
        total_ok += int(result["total"] == 2)
        fields_ok += int(
            {"total", "conflicts"} <= set(result)
            and all(
                {"type", "intent_a", "intent_b"} <= set(c)
                for c in result["conflicts"]
            )
        )
        via_mcp = server._call_tool(
            "intent_conflicts", {"time_window_minutes": 60}
        )
        mcp_ok += int(via_mcp["total"] == 2)
    return {
        "stores": 10,
        "time_ok": time_ok,
        "gap_ok": gap_ok,
        "context_ok": context_ok,
        "no_ok": no_ok,
        "total_ok": total_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "intent_conflicts_eval.json"),
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
