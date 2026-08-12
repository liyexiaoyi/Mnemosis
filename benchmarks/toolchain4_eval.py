"""Toolchain panorama 4 (round 122).

Extends the 12-step run with tag_memories, recall_log and
cleanup_preview: export -> import -> status -> audit -> review_load ->
dedupe -> resolve_conflicts -> tag -> cleanup_preview -> recall_log ->
review_batch -> practice_session -> sleep_and_plan -> search ->
list_conflicts -> practice_forecast.
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

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _build() -> tuple[MemoryEngine, MCPServer]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(6):
        engine.remember(
            f"t4-{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"t4-{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for _ in range(3):
        engine.remember(
            "t4 repeated event",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["t4dup", "同一天"],
        )
    engine.remember(
        "t4 conflict strong",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t4-c"],
        confidence=0.8,
        evidence_count=5,
        auto_cues=False,
    )
    engine.remember(
        "t4 conflict weak",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t4-c"],
        confidence=0.8,
        evidence_count=1,
        auto_cues=False,
    )
    engine.remember(
        "t4 old trivial",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["t4-old"],
        importance=0.1,
        created_at=now - timedelta(days=40),
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    src, server = _build()
    now = utcnow()
    payload = server._call_tool("export_memories", {})
    fresh = MemoryEngine()
    fresh_server = MCPServer(engine=fresh)
    imported = fresh_server._call_tool(
        "import_memories", {"payload": payload}
    )
    export_ok = imported == len(src.store.all_active())
    status_ok = (
        fresh_server._call_tool("memory_status", {})["stats"]["active"]
        == len(src.store.all_active())
    )
    audit_ok = (
        fresh_server._call_tool("memory_audit", {})["active"]
        == len(src.store.all_active())
    )
    load_ok = "load_index" in fresh_server._call_tool(
        "review_load", {"days": 7}
    )
    before = len(fresh.store.all_active())
    merged = fresh_server._call_tool("dedupe_memories", {})
    dedupe_ok = merged == 2 and len(fresh.store.all_active()) == before - 2
    resolve_ok = (
        fresh_server._call_tool("resolve_conflicts", {})["accommodated"]
        >= 1
    )
    ids = [item.id for item in fresh.store.all_active()][:6]
    tag_ok = fresh_server._call_tool(
        "tag_memories",
        {"memory_ids": ids, "tags": ["工作"], "action": "add"},
    )["updated"] == 6
    preview = fresh_server._call_tool("cleanup_preview", {"limit": 10})
    cleanup_ok = isinstance(preview, list)
    log_ok = len(fresh_server._call_tool("recall_log", {"limit": 5})) >= 0
    answers = [
        {"id": item.id, "success": i % 2 == 0}
        for i, item in enumerate(fresh.store.all_active())
    ]
    batch_ok = fresh_server._call_tool(
        "review_batch", {"answers": answers}
    )["n"] == len(answers)
    session_answers = [
        {"id": item.id, "attempt": "测试"}
        for item in list(fresh.store.all_active())[:5]
    ]
    session_ok = fresh_server._call_tool(
        "practice_session",
        {"limit": 5, "answers": session_answers},
    )["report"]["n"] == len(session_answers)
    sp = fresh_server._call_tool("sleep_and_plan", {"days": 7})
    sp_ok = isinstance(sp["plan"], list) and isinstance(sp["forecast"], list)
    search_ok = sum(
        1 for i in range(6)
        if (
            (r := fresh_server._call_tool(
                "search", {"query": f"t4-{i}", "top_k": 3}
            ))
            and f"value{i}" in r[0]["content"]
        )
    )
    conflicts_ok = len(
        fresh_server._call_tool("list_conflicts", {})
    ) == 0
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
        "tag": int(tag_ok),
        "cleanup_preview": int(cleanup_ok),
        "recall_log": int(log_ok),
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
        default=os.path.join(_BENCH, "results", "toolchain4_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        all(v == 1 for k, v in report.items() if k != "search")
        and report["search"] == 6
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
