"""Forgetting-export eval (round 165, Ebbinghaus 1885).

10 stores. Each store: a strong memory (strength 1.0) and a weak one
(0.3). forgetting_export must return a 31-point monotonic curve and show
the weak memory decaying faster.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str, str]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    m1 = engine.remember(
        f"forget strong {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=[f"fg-1{seed}"], strength=1.0, auto_cues=False,
    )
    m2 = engine.remember(
        f"forget weak {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=[f"fg-2{seed}"], strength=0.3, auto_cues=False,
    )
    return engine, MCPServer(engine=engine), m1.id, m2.id


def _run() -> dict:
    found_ok = points_ok = decay_ok = order_ok = weak_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, m1id, m2id = _store(seed)
        curve1 = engine.forgetting_export(m1id, days=30)
        curve2 = engine.forgetting_export(m2id, days=30)
        found_ok += int(curve1 is not None and curve2 is not None)
        points_ok += int(
            len(curve1["points"]) == 31
            and curve1["points"][0]["days_from_now"] == 0
            and curve1["points"][-1]["days_from_now"] == 30
        )
        decay_ok += int(curve1["final"] < curve1["initial"])
        order_ok += int(
            all(
                curve1["points"][i]["retrievability"]
                >= curve1["points"][i + 1]["retrievability"]
                for i in range(len(curve1["points"]) - 1)
            )
        )
        weak_ok += int(curve2["final"] < curve1["final"])
        fields_ok += int(
            {"memory_id", "content", "initial", "final", "points"}
            <= set(curve1)
            and all(
                {"days_from_now", "retrievability"} <= set(p)
                for p in curve1["points"]
            )
            and engine.forgetting_export("missing-id") is None
        )
        via_mcp = server._call_tool(
            "forgetting_export", {"memory_id": m1id, "days": 30}
        )
        mcp_ok += int(
            len(via_mcp["points"]) == 31
            and "initial" in via_mcp
        )
    return {
        "stores": 10,
        "found_ok": found_ok,
        "points_ok": points_ok,
        "decay_ok": decay_ok,
        "order_ok": order_ok,
        "weak_ok": weak_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "forgetting_export_eval.json"),
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
