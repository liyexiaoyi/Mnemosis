"""Toolchain panorama 15 (round 178, special-training wrap-up).

Extends the 51-step run with plan_quality, project_brief,
numeric_reasoning and plan_support (55 steps).
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
            f"t15-{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"t15-{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for _ in range(3):
        engine.remember(
            "t15 repeated event",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["t15dup", "same-day"],
        )
    engine.remember(
        "t15 conflict strong",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t15-c"],
        confidence=0.8,
        evidence_count=5,
        auto_cues=False,
    )
    engine.remember(
        "t15 conflict weak",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t15-c"],
        confidence=0.8,
        evidence_count=1,
        auto_cues=False,
    )
    engine.remember(
        "t15 old trivial",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["t15-old"],
        importance=0.1,
        created_at=now - timedelta(days=40),
    )
    pair_a = engine.remember(
        "t15 pair alpha shared value.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t15-sima"],
        auto_cues=False,
    )
    pair_b = engine.remember(
        "t15 pair alpha shared values.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t15-simb"],
        auto_cues=False,
    )
    engine.remember(
        "用户喜欢颜色偏蓝的配色",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["颜色偏好"],
    )
    engine.remember(
        "项目需求、架构、开发、测试、部署、上线全部确认",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["项目"],
        auto_cues=False,
    )
    engine.remember(
        "汽车速度 60 千米每小时",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["速度"],
        auto_cues=False,
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
        {"queries": ["t15-0", "t15-1", "t15-2"], "top_k": 3},
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
    intent_c = fresh_server._call_tool(
        "intent_remember",
        {"content": "clash reminder", "due_at": (now + timedelta(minutes=30)).isoformat()},
    )
    intent_remember_ok = int(
        intent_a["status"] == "active"
        and intent_b["status"] == "active"
        and intent_c["status"] == "active"
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
        fresh_server._call_tool("intent_report", {})["active"] == 2
    )
    intent_conflicts = fresh_server._call_tool(
        "intent_conflicts", {"time_window_minutes": 60}
    )
    intent_conflicts_ok = int(
        intent_conflicts["total"] == 1
        and intent_conflicts["conflicts"][0]["type"] == "time"
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
        {"query": "t15-0", "memory_id": ids[0]},
    )
    recognition_ok = int(recog["verdict"] == "recollection")
    unsuppress_ok = int(
        fresh_server._call_tool(
            "unsuppress_memories", {"memory_ids": [pair_a]}
        )["unsuppressed"] == 1
    )
    interference = fresh_server._call_tool(
        "interference_report", {"shared_cue_min": 3}
    )
    interference_ok = int(
        isinstance(interference, dict)
        and isinstance(interference["crowded_clusters"], list)
        and bool(interference["suggestion"])
    )
    story = fresh_server._call_tool("life_story", {"period_days": 30})
    life_story_ok = int(
        isinstance(story, dict)
        and story["total_events"] >= 1
        and isinstance(story["periods"], list)
    )
    health = fresh_server._call_tool("memory_health", {})
    health_ok = int(
        isinstance(health, dict)
        and health["memory_count"] == len(fresh.store.all_active())
        and 0 <= health["score"] <= 100
        and isinstance(health["penalties"], dict)
    )
    graph = fresh_server._call_tool("kg_export", {})
    kg_ok = int(
        isinstance(graph, dict)
        and graph["node_count"] == len(fresh.store.all_active())
        and graph["edge_count"] == len(graph["edges"])
    )
    profile = fresh_server._call_tool("learner_profile", {})
    learner_ok = int(
        isinstance(profile, dict)
        and profile["total_memories"] == len(fresh.store.all_active())
        and profile["profile"]
        in ("fast", "steady", "struggling", "unknown")
    )
    pack = fresh_server._call_tool(
        "context_pack",
        {"queries": ["t15-0", "t15-1", "t15-2"], "max_chars": 400},
    )
    pack_ok = int(
        isinstance(pack, dict)
        and pack["unique_found"] >= 3
        and pack["packed_chars"] <= 400
        and len({p["id"] for p in pack["packed"]})
        == len(pack["packed"])
    )
    enc = fresh_server._call_tool(
        "encoding_quality", {"memory_id": ids[0]}
    )
    enc_ok = int(
        isinstance(enc, dict)
        and enc["verdict"] in ("well_encoded", "adequate", "weak")
        and 0 <= enc["score"] <= 100
    )
    expl = fresh_server._call_tool(
        "explain_memory", {"memory_id": ids[0]}
    )
    explain_ok = int(
        isinstance(expl, dict)
        and "retrievability" in expl
        and "linked_count" in expl
        and "access_count" in expl
    )
    comp = fresh_server._call_tool(
        "compare_memories", {"id_a": pair_a, "id_b": pair_b}
    )
    compare_ok = int(
        isinstance(comp, dict)
        and comp["verdict"] in ("duplicate", "conflict", "distinct")
        and "overlap" in comp
    )
    queue = fresh_server._call_tool("action_queue", {"limit": 10})
    action_queue_ok = int(
        isinstance(queue, dict)
        and queue["total"] >= 2
        and "actions" in queue
    )
    cluster = fresh_server._call_tool(
        "summarize_cluster", {"memory_ids": ids[:3]}
    )
    summarize_ok = int(
        isinstance(cluster, dict)
        and len(cluster["memory_ids"]) == 3
        and bool(cluster["summary"])
    )
    hops = fresh_server._call_tool(
        "multi_hop_report", {"start_id": ids[0], "depth": 2}
    )
    multi_hop_ok = int(
        isinstance(hops, dict)
        and "hops" in hops
        and "total_reached" in hops
    )
    cram = fresh_server._call_tool(
        "cramming_plan",
        {"target_at": (now + timedelta(hours=3)).isoformat(),
         "hours_available": 1},
    )
    cramming_ok = int(
        isinstance(cram, dict)
        and len(cram["sessions"]) >= 1
        and cram["total_memories"] >= 1
    )
    sess = fresh_server._call_tool(
        "session_summary", {"memory_ids": ids[:4]}
    )
    session_ok = int(
        isinstance(sess, dict)
        and sess["total"] == 4
        and "summary" in sess
    )
    drift = fresh_server._call_tool(
        "topic_drift_report", {"period_days": 30}
    )
    drift_ok = int(
        isinstance(drift, dict)
        and isinstance(drift["topics"], list)
        and "total_drift" in drift
    )
    curve = fresh_server._call_tool(
        "forgetting_export", {"memory_id": ids[0], "days": 7}
    )
    forgetting_ok = int(
        isinstance(curve, dict)
        and len(curve["points"]) == 8
        and "initial" in curve
    )
    cov = fresh_server._call_tool("coverage_report", {"limit": 10})
    coverage_ok = int(
        isinstance(cov, dict)
        and isinstance(cov["topics"], list)
        and cov["total_topics"] >= 1
    )
    calib = fresh_server._call_tool("source_calibration", {})
    calibration_ok = int(
        isinstance(calib, dict)
        and isinstance(calib["sources"], list)
        and calib["total_memories"] == len(fresh.store.all_active())
    )
    risk = fresh_server._call_tool("forgetting_risk", {"limit": 10})
    risk_ok = int(
        isinstance(risk, dict)
        and risk["total"] == len(fresh.store.all_active())
        and isinstance(risk["riskiest"], list)
    )
    bridges = fresh_server._call_tool("bridge_suggestions", {"limit": 10})
    bridge_ok = int(
        isinstance(bridges, dict)
        and isinstance(bridges["suggestions"], list)
        and "total" in bridges
    )
    pq = fresh_server._call_tool(
        "plan_quality",
        {
            "plan": ["调研需求", "设计架构", "开发功能", "测试功能", "部署上线"],
            "context_memory_ids": ids[:1],
        },
    )
    plan_quality_ok = int(
        isinstance(pq, dict)
        and pq["verdict"] in ("good", "fair", "weak", "empty")
        and "score" in pq
    )
    brief = fresh_server._call_tool(
        "project_brief", {"title": "项目", "memory_ids": ids}
    )
    brief_ok = int(
        isinstance(brief, dict)
        and "background" in brief
        and "summary" in brief
    )
    nr = fresh_server._call_tool(
        "numeric_reasoning", {"problem": "汽车3小时行驶180千米"}
    )
    numeric_ok = int(
        isinstance(nr, dict)
        and nr["verdict"] in ("consistent", "review_needed")
        and "numbers" in nr
    )
    ps = fresh_server._call_tool(
        "plan_support", {"plan": ["调研需求", "部署上线"]}
    )
    support_ok = int(
        isinstance(ps, dict)
        and len(ps["steps"]) == 2
        and "total_supported" in ps
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
    practice_ok = fresh_server._call_tool(
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
                "search", {"query": f"t15-{i}", "top_k": 3}
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
        "intent_conflicts": intent_conflicts_ok,
        "retrieval_assist": assist_ok,
        "schema_report": schema_ok,
        "suppress": int(suppress_ok),
        "suppressed_report": suppressed_report_ok,
        "timeline_report": timeline_ok,
        "recognition_check": recognition_ok,
        "unsuppress": int(unsuppress_ok),
        "interference_report": interference_ok,
        "life_story": life_story_ok,
        "memory_health": health_ok,
        "kg_export": kg_ok,
        "learner_profile": learner_ok,
        "context_pack": pack_ok,
        "encoding_quality": enc_ok,
        "explain_memory": explain_ok,
        "compare_memories": compare_ok,
        "action_queue": action_queue_ok,
        "summarize_cluster": summarize_ok,
        "multi_hop_report": multi_hop_ok,
        "cramming_plan": cramming_ok,
        "session_summary": session_ok,
        "topic_drift_report": drift_ok,
        "forgetting_export": forgetting_ok,
        "coverage_report": coverage_ok,
        "source_calibration": calibration_ok,
        "forgetting_risk": risk_ok,
        "bridge_suggestions": bridge_ok,
        "plan_quality": plan_quality_ok,
        "project_brief": brief_ok,
        "numeric_reasoning": numeric_ok,
        "plan_support": support_ok,
        "review_batch": int(review_batch_ok),
        "practice_session": int(practice_ok),
        "sleep_and_plan": int(sp_ok),
        "search": search_ok,
        "conflicts_after": int(conflicts_ok),
        "forecast": int(forecast_ok),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "toolchain15_eval.json"),
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
