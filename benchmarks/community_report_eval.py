"""Community-report eval (round 195, network community structure).

10 stores. Each store: 2 linked clusters (4+2) and 2 isolated memories.
community_report must find 4 communities, largest 4.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for name in ("a1", "a2", "a3", "a4"):
        engine.remember(
            f"zzz {name} {seed}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["社区a"],
            auto_cues=False,
        )
    for name in ("b1", "b2"):
        engine.remember(
            f"zzz {name} {seed}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["社区b"],
            auto_cues=False,
        )
    engine.remember(
        f"zzz c1 {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=[f"独一{seed}"], auto_cues=False,
    )
    engine.remember(
        f"zzz c2 {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=[f"独二{seed}"], auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = largest_ok = sizes_ok = cues_ok = members_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.community_report()
        total_ok += int(report["total_communities"] == 4)
        largest_ok += int(report["largest_size"] == 4)
        sizes_ok += int(
            sorted(c["size"] for c in report["communities"]) == [1, 1, 2, 4]
        )
        community_a = next(
            c for c in report["communities"] if c["size"] == 4
        )
        cues_ok += int("社区a" in community_a["top_cues"])
        members_ok += int(
            all(c["members"] for c in report["communities"])
        )
        fields_ok += int(
            {"total_communities", "largest_size", "communities"}
            <= set(report)
            and all(
                {"id", "size", "members", "top_cues"} <= set(c)
                for c in report["communities"]
            )
        )
        via_mcp = server._call_tool("community_report", {"limit": 10})
        mcp_ok += int(
            via_mcp["largest_size"] == 4
            and via_mcp["total_communities"] == 4
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "largest_ok": largest_ok,
        "sizes_ok": sizes_ok,
        "cues_ok": cues_ok,
        "members_ok": members_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "community_report_eval.json"),
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
