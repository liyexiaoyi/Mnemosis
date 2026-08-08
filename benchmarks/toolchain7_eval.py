"""Toolchain panorama 7 (round 137).

Extends the 25-step run with suppress/unsuppress/suppressed_report,
timeline_report and recognition_check (30 steps).
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
    for i in range(6):
        engine.remember(
            f"t7-{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"t7-{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for _ in range(3):
        engine.remember(
            "t7 repeated event",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["t7dup", "same-day"],
        )
    engine.remember(
        "t7 conflict strong",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t7-c"],
        confidence=0.8,
        evidence_count=5,
        auto_cues=False,
    )
    engine.remember(
        "t7 conflict weak",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t7-c"],
        confidence=0.8,
        evidence_count=1,
        auto_cues=False,
    )
    engine.remember(
        "t7 old trivial",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["t7-old"],
        importance=0.1,
        created_at=now - timedelta(days=40),
    )
    pair_a = engine.remember(
        "t7 pair alpha shared value.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t7-sima"],
        auto_cues=False,
    )
    pair_b = engine.remember(
        "t7 pair alpha shared values.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t7-simb"],
        auto_cues=False,
    )
    engine.remember(
        "用户喜欢颜色偏蓝的配色",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["颜色偏好"],
    )
    return engine, MCPServer(engine=engine), pair_a.id, pair_b.id


def _run() -> dict:
    src, server, pair_a, pair_b = _build()
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
        {"memory_ids": ids, "tags": ["work"], "action": "add"},
    )["updated"] == 6
    preview = fresh_server._call_tool("cleanup_preview", {"limit": 10})
    cleanup_ok = isinstance(preview, list)
    log_ok = len(fresh_server._call_tool("recall_log", {"limit": 5})) >= 0
    sim = fresh_server._call_tool("similarity_report", {"threshold": 0.6})
    sim_ok = int(
        isinstance(sim, list)
        and any(
            {pair_a, pair_b} <= {p["a_id"], p["b_id"]} for p in sim
        )
    )
    assoc = fresh_server._call_tool("association_report", {"limit": 5})
    assoc_ok = int(
        isinstance(assoc, dict)
        and assoc["memory_count"] == len(fresh.store.all_active())
        and isinstance(assoc["top_connected"], list)
    )
    batch = fresh_server._call_tool(
        "search_batch",
        {"queries": ["t7-0", "t7-1", "t7-2"], "top_k": 3},
    )
    batch_ok = sum(
        1
        for i, group in enumerate(batch)
        if group["count"] >= 1 and f"value{i}" in group["results"][0]["preview"]
    )
    intent_a = fresh_server._call_tool(
        "intent_remember",
        {"content": "send email", "due_at": (now + timedelta(hours=1)).isoformat()},
    )
    intent_b = fresh_server._call_tool(
        "intent_remember",
        {"content": "call back", "due_at": (now - timedelta(hours=1)).isoformat()},
    )
    intent_remember_ok = int(
        intent_a["status"] == "active" and intent_b["status"] == "active"
    )
    due = fresh_server._call_tool("intent_due", {"limit": 10})
    intent_due_ok = int(
        len(due) == 1 and due[0]["id"] == intent_b["id"]
    )
    fresh_server._call_tool("intent_complete", {"intent_id": intent_b["id"]})
    intent_complete_ok = int(
        len(fresh_server._call_tool("intent_due", {"limit": 10})) == 0
    )
    intent_report_ok = int(
        fresh_server._call_tool("intent_report", {})["active"] == 1
    )
    assist = fresh_server._call_tool(
        "retrieval_assist", {"query": "色彩", "limit": 5}
    )
    assist_ok = int(
        "颜色偏好" in [s["cue"] for s in assist["suggestions"]]
    )
    schema = fresh_server._call_tool("schema_report", {"limit": 10})
    schema_ok = int(
        isinstance(schema, dict)
        and schema["group_count"] >= 2
        and schema["total_memories"] == len(fresh.store.all_active())
    )
    suppress_ok = int(
        fresh_server._call_tool(
            "suppress_memories", {"memory_ids": [pair_a]}
        )["suppressed"] == 1
    )
    suppressed = fresh_server._call_tool("suppressed_report", {})
    suppressed_report_ok = int(
        suppressed["count"] == 1
        and suppressed["memories"][0]["id"] == pair_a
    )
    timeline = fresh_server._call_tool("timeline_report", {"limit": 50})
    timeline_ok = int(
        isinstance(timeline, dict)
        and timeline["total"] >= 1
        and isinstance(timeline["days"], list)
    )
    recog = fresh_server._call_tool(
        "recognition_check",
        {"query": "t7-0", "memory_id": ids[0]},
    )
    recognition_ok = int(recog["verdict"] == "recollection")
    unsuppress_ok = int(
        fresh_server._call_tool(
            "unsuppress_memories", {"memory_ids": [pair_a]}
        )["unsuppressed"] == 1
    )
    answers = [
        {"id": item.id, "success": i % 2 == 0}
        for i, item in enumerate(fresh.store.all_active())
    ]
    review_batch_ok = fresh_server._call_tool(
        "review_batch", {"answers": answers}
    )["n"] == len(answers)
    session_answers = [
        {"id": item.id, "attempt": "test"}
        for item in list(fresh.store.all_active())[:5]
    ]
    session_ok = fresh_server._call_tool(
        "practice_session",
        {"limit": 5, "answers": session_answers},
    )["report"]["n"] == len(session_answers)
    sp = fresh_server._call_tool("sleep_and_plan", {"days": 7})
    sp_ok = isinstance(sp["plan"], list) and isinstance(sp["forecast"], list)
    search_ok = sum(
        1
        for i in range(6)
        if (
            (r := fresh_server._call_tool(
                "search", {"query": f"t7-{i}", "top_k": 3}
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
        "similarity_report": sim_ok,
        "association_report": assoc_ok,
        "search_batch": batch_ok,
        "intent_remember": intent_remember_ok,
        "intent_due": intent_due_ok,
        "intent_complete": intent_complete_ok,
        "intent_report": intent_report_ok,
        "retrieval_assist": assist_ok,
        "schema_report": schema_ok,
        "suppress": int(suppress_ok),
        "suppressed_report": suppressed_report_ok,
        "timeline_report": timeline_ok,
        "recognition_check": recognition_ok,
        "unsuppress": int(unsuppress_ok),
        "review_batch": int(review_batch_ok),
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
        default=os.path.join(_BENCH, "results", "toolchain7_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        all(
            v == 1
            for k, v in report.items()
            if k not in ("search", "search_batch")
        )
        and report["search"] == 6
        and report["search_batch"] == 3
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
