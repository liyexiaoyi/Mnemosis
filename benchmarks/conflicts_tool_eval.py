"""MCP list_conflicts tool eval (round 99).

8 true conflict pairs (same cue, both confident, different content) and
8 non-conflict pairs (same cue, one side low-confidence). The MCP tool
should return exactly the 8 true conflicts and no false positives.
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


def _build() -> tuple[MemoryEngine, MCPServer]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(8):
        engine.remember(
            f"conflict{i} v1",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"conflict{i}"],
            confidence=0.8,
            auto_cues=False,
        )
        engine.remember(
            f"conflict{i} v2",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"conflict{i}"],
            confidence=0.8,
            auto_cues=False,
        )
        engine.remember(
            f"calm{i} a",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"calm{i}"],
            confidence=0.2,
            auto_cues=False,
        )
        engine.remember(
            f"calm{i} b",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"calm{i}"],
            confidence=0.8,
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    engine, server = _build()
    conflicts = server._call_tool("list_conflicts", {})
    true_ids = set()
    for i in range(8):
        for item in engine.backend.find_by_cue(f"conflict{i}"):
            true_ids.add(item.id)
    reported_ids = set()
    for c in conflicts:
        reported_ids.add(c["a_id"])
        reported_ids.add(c["b_id"])
    hits = len(true_ids & reported_ids)
    false_pos = len(reported_ids - true_ids)
    return {
        "true_conflict_ids": len(true_ids),
        "reported_conflict_ids": len(reported_ids),
        "hits": hits,
        "false_positives": false_pos,
        "reported_pairs": len(conflicts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "conflicts_tool_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["reported_pairs"] == 8
        and report["hits"] == 16
        and report["false_positives"] == 0
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
