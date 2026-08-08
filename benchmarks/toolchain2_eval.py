"""Toolchain panorama 2 (round 112).

Extends round 107 with the new aggregation tools:
  export -> import -> memory_status -> memory_audit -> review_batch ->
  practice_session -> sleep_and_plan -> search -> list_conflicts ->
  practice_forecast.
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
            f"t2-{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"t2-{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for i in range(3):
        engine.remember(
            f"t2 weak-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"t2w-{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=60),
            auto_cues=False,
        )
    engine.remember(
        "t2 conflict a",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t2-c"],
        confidence=0.8,
        auto_cues=False,
    )
    engine.remember(
        "t2 conflict b",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t2-c"],
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
    status_ok = (
        fresh_server._call_tool("memory_status", {})["stats"]["active"]
        == len(src.store.all_active())
    )
    # 3) audit
    audit = fresh_server._call_tool("memory_audit", {})
    audit_ok = audit["active"] == len(src.store.all_active())
    # 4) review batch
    answers = [
        {"id": item.id, "success": i % 2 == 0}
        for i, item in enumerate(fresh.store.all_active())
    ]
    batch_ok = fresh_server._call_tool(
        "review_batch", {"answers": answers}
    )["n"] == len(answers)
    # 5) practice session
    session_answers = [
        {"id": item.id, "attempt": "测试"}
        for item in list(fresh.store.all_active())[:5]
    ]
    session = fresh_server._call_tool(
        "practice_session",
        {"limit": 5, "answers": session_answers},
    )
    session_ok = session["report"]["n"] == len(session_answers)
    # 6) sleep + plan
    sp = fresh_server._call_tool("sleep_and_plan", {"days": 7})
    sp_ok = (
        isinstance(sp["plan"], list)
        and isinstance(sp["forecast"], list)
        and "weak_replayed" in sp["sleep_summary"]
    )
    # 7) search
    search_ok = sum(
        1 for i in range(10)
        if (
            (r := fresh_server._call_tool(
                "search", {"query": f"t2-{i}", "top_k": 3}
            ))
            and f"value{i}" in r[0]["content"]
        )
    )
    # 8) conflicts
    conflicts_ok = len(
        fresh_server._call_tool("list_conflicts", {})
    ) == 1
    # 9) forecast
    forecast_ok = len(
        fresh.practice_forecast(days=7, now=now)
    ) > 0
    return {
        "export_import": int(export_ok),
        "status": int(status_ok),
        "audit": int(audit_ok),
        "review_batch": int(batch_ok),
        "practice_session": int(session_ok),
        "sleep_and_plan": int(sp_ok),
        "search": search_ok,
        "conflicts": int(conflicts_ok),
        "forecast": int(forecast_ok),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "toolchain2_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        all(v == 1 for k, v in report.items() if k != "search")
        and report["search"] == 10
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
