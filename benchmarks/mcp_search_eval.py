"""MCP search tool eval (round 95).

20 semantic memories; 10 queries through the MCP `search` tool. Every
call should return the correct top-1 content with score, confidence flag
and reasons (all retrieval mechanisms apply through the tool).
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


def _build() -> tuple[MemoryEngine, MCPServer]:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(20):
        engine.remember(
            f"项目{i}：负责人编号{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"proj{i}"],
            importance=0.5 + 0.02 * i,
            strength=0.5,
            created_at=now - timedelta(days=5 + i),
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    engine, server = _build()
    correct = 0
    fields_ok = 0
    for i in range(10):
        results = server._call_tool(
            "search", {"query": f"proj{i}", "top_k": 3}
        )
        if results and f"项目{i}" in results[0]["content"]:
            correct += 1
        if (
            results
            and all(
                key in results[0]
                for key in ("id", "content", "score", "confident", "reasons")
            )
        ):
            fields_ok += 1
    return {
        "queries": 10,
        "correct_top1": correct,
        "fields_ok": fields_ok,
        "total_memories": len(engine.store.all_active()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "mcp_search_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["correct_top1"] == report["queries"]
        and report["fields_ok"] == report["queries"]
        and report["total_memories"] == 20
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
