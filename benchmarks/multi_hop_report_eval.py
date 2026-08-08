"""Multi-hop-report eval (round 159, Collins & Loftus 1975).

10 stores. Each store: a chain a-b-c-d plus branch b-e. multi_hop_report
must list hop-1, hop-2 and hop-3 neighbours correctly and count reached
memories.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    items = [
        engine.remember(
            f"zzz {letter} {seed}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"mh-{letter}{seed}"],
            auto_cues=False,
        )
        for letter in ("a", "b", "c", "d", "e")
    ]
    a, b, c, d, e = [item.id for item in items]
    engine.backend.add_link(a, b)
    engine.backend.add_link(b, c)
    engine.backend.add_link(c, d)
    engine.backend.add_link(b, e)
    return engine, MCPServer(engine=engine), a


def _run() -> dict:
    hop1_ok = hop2_ok = depth_ok = reached_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, a = _store(seed)
        report = engine.multi_hop_report(a, depth=2)
        hop1_ok += int(
            len(report["hops"][0]["memory_ids"]) == 1
        )
        hop2_ok += int(
            len(report["hops"][1]["memory_ids"]) == 2
            and report["hops"][1]["count"] == 2
        )
        deep = engine.multi_hop_report(a, depth=3)
        depth_ok += int(
            len(deep["hops"]) == 3
            and deep["hops"][2]["count"] == 1
        )
        reached_ok += int(
            deep["total_reached"] == 4
            and len(deep["reached_ids"]) == 4
        )
        fields_ok += int(
            {"start_id", "depth", "hops", "total_reached", "reached_ids"}
            <= set(report)
            and all(
                {"hop", "memory_ids", "count"} <= set(h)
                for h in report["hops"]
            )
            and engine.multi_hop_report("missing-id") is None
        )
        via_mcp = server._call_tool(
            "multi_hop_report", {"start_id": a, "depth": 3}
        )
        mcp_ok += int(via_mcp["total_reached"] == 4)
    return {
        "stores": 10,
        "hop1_ok": hop1_ok,
        "hop2_ok": hop2_ok,
        "depth_ok": depth_ok,
        "reached_ok": reached_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "multi_hop_report_eval.json"),
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
