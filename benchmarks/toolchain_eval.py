"""Toolchain panorama eval (round 107).

One store, every MCP/engine tool in sequence:
  export -> import (fresh engine) -> memory_status -> review_batch ->
  search -> list_conflicts -> practice_forecast.
Each step must produce correct results on the same data.
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
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(10):
        engine.remember(
            f"tool{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"tool{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    engine.remember(
        "tool conflict a",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["tool-conflict"],
        confidence=0.8,
        auto_cues=False,
    )
    engine.remember(
        "tool conflict b",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["tool-conflict"],
        confidence=0.8,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    src, server = _build()
    now = utcnow()
    # 1) export -> import
    payload = server._call_tool("export_memories", {})
    fresh = MemoryEngine()
    fresh_server = MCPServer(engine=fresh)
    imported = fresh_server._call_tool(
        "import_memories", {"payload": payload}
    )
    export_ok = imported == len(src.store.all_active())
    # 2) status
    status = fresh_server._call_tool("memory_status", {})
    status_ok = status["stats"]["active"] == len(src.store.all_active())
    # 3) review batch on fresh
    answers = [
        {"id": item.id, "success": i % 2 == 0}
        for i, item in enumerate(fresh.store.all_active())
    ]
    batch = fresh_server._call_tool(
        "review_batch", {"answers": answers}
    )
    batch_ok = batch["n"] == len(answers) and batch["successes"] >= 5
    # 4) search
    search_ok = sum(
        1 for i in range(10)
        if (
            (r := fresh_server._call_tool(
                "search", {"query": f"tool{i}", "top_k": 3}
            ))
            and f"value{i}" in r[0]["content"]
        )
    )
    # 5) conflicts
    conflicts = fresh_server._call_tool("list_conflicts", {})
    conflicts_ok = len(conflicts) == 1
    # 6) forecast
    forecast = fresh.practice_forecast(days=7, now=now)
    forecast_ok = len(forecast) > 0
    return {
        "export_import": int(export_ok),
        "status": int(status_ok),
        "review_batch": int(batch_ok),
        "search_ok": search_ok,
        "conflicts": int(conflicts_ok),
        "forecast": int(forecast_ok),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "toolchain_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["export_import"] == 1
        and report["status"] == 1
        and report["review_batch"] == 1
        and report["search_ok"] == 10
        and report["conflicts"] == 1
        and report["forecast"] == 1
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
