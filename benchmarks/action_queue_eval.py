"""Action-queue eval (round 155, Anderson 1983 ACT-R).

10 stores. Each store registers 6 intentions: 1 overdue, 2 urgent, 1
far-away, 2 clashing on the same context cue. action_queue must order
overdue first, flag urgency/clashes and count correctly.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str, str]:
    engine = MemoryEngine()
    now = utcnow()
    i1 = engine.remember_intent(
        f"soon a {seed}", due_at=now + timedelta(minutes=10)
    )
    i2 = engine.remember_intent(
        f"soon b {seed}", due_at=now + timedelta(minutes=20)
    )
    i3 = engine.remember_intent(
        f"later {seed}", due_at=now + timedelta(hours=2)
    )
    i4 = engine.remember_intent(
        f"overdue {seed}", due_at=now - timedelta(hours=1)
    )
    engine.remember_intent(
        f"office a {seed}", due_at=now + timedelta(days=1),
        context_cue="office",
    )
    engine.remember_intent(
        f"office b {seed}", due_at=now + timedelta(days=2),
        context_cue="office",
    )
    return engine, MCPServer(engine=engine), i1["id"], i3["id"], i4["id"]


def _run() -> dict:
    total_ok = overdue_ok = order_ok = urgent_ok = clash_ok = fields_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine, server, i1id, i3id, i4id = _store(seed)
        queue = engine.action_queue(now=utcnow())
        total_ok += int(queue["total"] == 6)
        overdue_ok += int(
            queue["overdue"] == 1
            and queue["actions"][0]["intent_id"] == i4id
        )
        by_id = {a["intent_id"]: a for a in queue["actions"]}
        due_order = [a["due_at"] for a in queue["actions"][1:]]
        order_ok += int(due_order == sorted(due_order))
        urgent_ok += int(
            by_id[i1id]["urgent"] and not by_id[i3id]["urgent"]
        )
        clash_ok += int(
            by_id[i1id]["clash"] and not by_id[i3id]["clash"]
            and queue["clashes"] == 4
        )
        fields_ok += int(
            {"total", "overdue", "upcoming", "clashes", "actions"} <= set(queue)
            and all(
                {"type", "intent_id", "content", "due_at", "overdue",
                 "urgent", "clash"} <= set(a)
                for a in queue["actions"]
            )
        )
        via_mcp = server._call_tool("action_queue", {"limit": 10})
        mcp_ok += int(
            via_mcp["total"] == 6 and via_mcp["overdue"] == 1
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "overdue_ok": overdue_ok,
        "order_ok": order_ok,
        "urgent_ok": urgent_ok,
        "clash_ok": clash_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "action_queue_eval.json"),
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
