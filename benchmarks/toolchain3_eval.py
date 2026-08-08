"""Toolchain panorama 3 (round 117).

Extends the 9-step run with dedupe_memories, resolve_conflicts and
review_load:
  export -> import -> status -> audit -> review_load -> dedupe ->
  resolve_conflicts -> review_batch -> practice_session -> sleep_and_plan
  -> search -> list_conflicts -> practice_forecast.
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
    for i in range(8):
        engine.remember(
            f"t3-{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"t3-{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for _ in range(3):
        engine.remember(
            "t3 repeated event",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["t3dup", "同一天"],
        )
    engine.remember(
        "t3 conflict strong",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t3-c"],
        confidence=0.8,
        evidence_count=5,
        auto_cues=False,
    )
    engine.remember(
        "t3 conflict weak",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t3-c"],
        confidence=0.8,
        evidence_count=1,
        auto_cues=False,
    )
    engine.remember(
        "t3 weak-important",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t3w"],
        importance=0.8,
        strength=0.3,
        created_at=now - timedelta(days=60),
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
    audit_ok = (
        fresh_server._call_tool("memory_audit", {})["active"]
        == len(src.store.all_active())
    )
    # 4) review load
    load = fresh_server._call_tool("review_load", {"days": 7})
    load_ok = "load_index" in load
    # 5) dedupe
    before = len(fresh.store.all_active())
    merged = fresh_server._call_tool("dedupe_memories", {})
    dedupe_ok = merged == 2 and len(fresh.store.all_active()) == before - 2
    # 6) resolve conflicts
    resolved = fresh_server._call_tool("resolve_conflicts", {})
    resolve_ok = resolved["accommodated"] >= 1
    # 7) review batch
    answers = [
        {"id": item.id, "success": i % 2 == 0}
        for i, item in enumerate(fresh.store.all_active())
    ]
    batch_ok = fresh_server._call_tool(
        "review_batch", {"answers": answers}
    )["n"] == len(answers)
    # 8) practice session
    session_answers = [
        {"id": item.id, "attempt": "测试"}
        for item in list(fresh.store.all_active())[:5]
    ]
    session_ok = fresh_server._call_tool(
        "practice_session",
        {"limit": 5, "answers": session_answers},
    )["report"]["n"] == len(session_answers)
    # 9) sleep + plan
    sp = fresh_server._call_tool("sleep_and_plan", {"days": 7})
    sp_ok = isinstance(sp["plan"], list) and isinstance(sp["forecast"], list)
    # 10) search
    search_ok = sum(
        1 for i in range(8)
        if (
            (r := fresh_server._call_tool(
                "search", {"query": f"t3-{i}", "top_k": 3}
            ))
            and f"value{i}" in r[0]["content"]
        )
    )
    # 11) conflicts
    conflicts_ok = len(
        fresh_server._call_tool("list_conflicts", {})
    ) == 0
    # 12) forecast
    forecast_ok = len(
        fresh.practice_forecast(days=7, now=now)
    ) > 0
    return {
        "export_import": int(export_ok),
        "status": int(status_ok),
        "audit": int(audit_ok),
        "review_load": int(load_ok),
        "dedupe": int(dedupe_ok),
        "resolve_conflicts": int(resolve_ok),
        "review_batch": int(batch_ok),
        "practice_session": int(session_ok),
        "sleep_and_plan": int(sp_ok),
        "search": search_ok,
        "conflicts_after": int(conflicts_ok),
        "forecast": int(forecast_ok),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "toolchain3_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        all(v == 1 for k, v in report.items() if k != "search")
        and report["search"] == 8
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
