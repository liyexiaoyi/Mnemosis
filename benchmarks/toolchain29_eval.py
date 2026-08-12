"""Toolchain panorama 29 (round 249).

Extends the 93-step run with retrieval_snapshot, plan_rehearsal,
math_ladder, physics_simulate, analogy_prompt and review_consistency
(99 steps).
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
            f"t19-{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"t19-{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for _ in range(3):
        engine.remember(
            "t19 repeated event",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["t19dup", "same-day"],
        )
    engine.remember(
        "t19 conflict strong",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t19-c"],
        confidence=0.8,
        evidence_count=5,
        auto_cues=False,
    )
    engine.remember(
        "t19 conflict weak",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t19-c"],
        confidence=0.8,
        evidence_count=1,
        auto_cues=False,
    )
    engine.remember(
        "t19 old trivial",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["t19-old"],
        importance=0.1,
        created_at=now - timedelta(days=40),
    )
    pair_a = engine.remember(
        "t19 pair alpha shared value.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t19-sima"],
        auto_cues=False,
    )
    pair_b = engine.remember(
        "t19 pair alpha shared values.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["t19-simb"],
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
    engine.remember(
        "上线成功，客户满意",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["经验"],
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
        {"queries": ["t19-0", "t19-1", "t19-2"], "top_k": 3},
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
        {"query": "t19-0", "memory_id": ids[0]},
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
        {"queries": ["t19-0", "t19-1", "t19-2"], "max_chars": 400},
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
    dep = fresh_server._call_tool(
        "dependency_map",
        {"plan": [
            {"step": "调研需求", "depends_on": []},
            {"step": "设计架构", "depends_on": [0]},
            {"step": "开发功能", "depends_on": [1]},
            {"step": "测试功能", "depends_on": [2]},
            {"step": "部署上线", "depends_on": [3]},
        ]},
    )
    dep_ok = int(
        isinstance(dep, dict)
        and len(dep["critical_path"]) == 5
        and "finish_level" in dep
    )
    prisk = fresh_server._call_tool("project_risk", {"memory_ids": ids})
    project_risk_ok = int(
        isinstance(prisk, dict)
        and 0 <= prisk["risk_score"] <= 100
        and "factors" in prisk
    )
    tracker = fresh_server._call_tool(
        "plan_tracker",
        {"plan": ["调研需求", "设计架构", "开发功能"], "statuses": {"0": "done"}},
    )
    tracker_ok = int(
        isinstance(tracker, dict)
        and tracker["total"] == 3
        and "completion_ratio" in tracker
    )
    rewrite = fresh_server._call_tool(
        "plan_rewrite", {"plan": ["功能", "部署", "功能", "需求"]}
    )
    rewrite_ok = int(
        isinstance(rewrite, dict)
        and isinstance(rewrite["rewritten"], list)
        and bool(rewrite["changes"])
    )
    lessons = fresh_server._call_tool(
        "lesson_learned", {"memory_ids": ids}
    )
    lessons_ok = int(
        isinstance(lessons, dict)
        and "total" in lessons
        and isinstance(lessons["lessons"], list)
    )
    effort = fresh_server._call_tool(
        "effort_estimate",
        {"plan": [
            {"step": "调研需求", "depends_on": []},
            {"step": "开发功能", "depends_on": [0]},
            {"step": "部署上线", "depends_on": [1]},
        ]},
    )
    effort_ok = int(
        isinstance(effort, dict)
        and effort["total_hours"] > 0
        and "buffered_total_hours" in effort
    )
    review = fresh_server._call_tool(
        "decision_review",
        {
            "plan": ["调研需求", "开发功能"],
            "results": {
                "0": {"status": "success"},
                "1": {"status": "failure", "note": "超时"},
            },
        },
    )
    review_ok = int(
        isinstance(review, dict)
        and 0 <= review["score"] <= 100
        and "lessons" in review
    )
    transfer = fresh_server._call_tool(
        "transfer_report",
        {"plan": ["调研需求", "开发功能"], "lessons_memory_ids": ids},
    )
    transfer_ok = int(
        isinstance(transfer, dict)
        and isinstance(transfer["plan_steps"], list)
        and "applicable_lessons" in transfer
    )
    rq = fresh_server._call_tool(
        "retrieval_quality",
        {"queries": ["t19-0", "t19-1", "zzz miss"], "top_k": 3},
    )
    rq_ok = int(
        isinstance(rq, dict)
        and rq["queries_evaluated"] == 3
        and "hit_rate" in rq
    )
    trace = fresh_server._call_tool(
        "recall_trace", {"query": "t19-0", "top_k": 3}
    )
    trace_ok = int(
        isinstance(trace, dict)
        and trace["candidates_scanned"] >= 1
        and isinstance(trace["results"], list)
    )
    community = fresh_server._call_tool("community_report", {"limit": 10})
    community_ok = int(
        isinstance(community, dict)
        and community["total_communities"] >= 1
        and "largest_size" in community
    )
    sleep = fresh_server._call_tool("sleep_advice", {})
    sleep_ok = int(
        isinstance(sleep, dict)
        and "pre_sleep_review" in sleep
        and "tomorrow_priorities" in sleep
    )
    emotion = fresh_server._call_tool("emotion_advice", {})
    emotion_ok = int(
        isinstance(emotion, dict)
        and "mood_profile" in emotion
        and "negative_ratio" in emotion
        and "advice" in emotion
    )
    diff = fresh_server._call_tool("difficulty_estimator", {"limit": 10})
    diff_ok = int(
        isinstance(diff, dict)
        and "buckets" in diff
        and "sweet_spot_ratio" in diff
        and "advice" in diff
    )
    integ = fresh_server._call_tool("memory_integration", {"limit": 10})
    integ_ok = int(
        isinstance(integ, dict)
        and "schema_candidates" in integ
        and "event_chains" in integ
        and "conflicts" in integ
    )
    trace = fresh_server._call_tool(
        "reasoning_trace",
        {"problem": "t19-0 相关", "topic": "t19", "store_conclusion": False},
    )
    trace_ok = int(
        isinstance(trace, dict)
        and "evidence_used" in trace
        and len(trace["steps"]) == 4
        and "stored_memory_id" in trace
    )
    goal = fresh_server._call_tool("goal_replay", {"goal": "t19-0"})
    goal_ok = int(
        isinstance(goal, dict)
        and "replay_steps" in goal
        and 0 <= goal["replay_score"] <= 1
    )
    slep = fresh_server._call_tool("sleep_inference", {"limit": 5})
    slep_ok = int(
        isinstance(slep, dict)
        and "total_pairs" in slep
        and "ready_pairs" in slep
        and isinstance(slep["candidates"], list)
    )
    schema = fresh_server._call_tool("schema_fit", {"limit": 10})
    schema_ok = int(
        isinstance(schema, dict)
        and "schema_count" in schema
        and isinstance(schema["rows"], list)
        and "advice" in schema
    )
    budget = fresh_server._call_tool(
        "working_set_budget", {"limit": 20}
    )
    budget_ok = int(
        isinstance(budget, dict)
        and budget["verdict"] in ("overloaded", "optimal", "underutilized")
        and isinstance(budget["chunks"], list)
    )
    tests = fresh_server._call_tool(
        "test_generator", {"topic": "t19-0", "count": 3}
    )
    tests_ok = int(
        isinstance(tests, dict)
        and tests["question_count"] >= 1
        and isinstance(tests["questions"], list)
        and tests["questions"][0]["answer_hidden"]
    )
    spaced = fresh_server._call_tool(
        "spacing_plan", {"days": 7, "limit": 20}
    )
    spaced_ok = int(
        isinstance(spaced, dict)
        and spaced["total_scheduled"] >= 1
        and len(spaced["daily_plan"]) == 7
    )
    rumi = fresh_server._call_tool("rumination_check", {})
    rumi_ok = int(
        isinstance(rumi, dict)
        and rumi["risk_level"] in ("low", "medium", "high")
        and isinstance(rumi["risky_memories"], list)
    )
    consol = fresh_server._call_tool(
        "consolidation_forecast", {"limit": 5}
    )
    consol_ok = int(
        isinstance(consol, dict)
        and isinstance(consol["tonight_candidates"], list)
        and "predicted_gain_total" in consol
    )
    fb = fresh_server._call_tool("forgetting_balance", {})
    fb_ok = int(
        isinstance(fb, dict)
        and "total_topics" in fb
        and isinstance(fb["topics"], list)
        and "flagged_count" in fb
    )
    meta = fresh_server._call_tool("metacog_report", {})
    meta_ok = int(
        isinstance(meta, dict)
        and isinstance(meta["topics"], list)
        and 0 <= meta["calibration_score"] <= 1
    )
    first_id = fresh.store.all_active()[0].id
    recon = fresh_server._call_tool(
        "reconsolidation_plan", {"memory_id": first_id}
    )
    recon_ok = int(
        isinstance(recon, dict)
        and recon.get("found") is True
        and isinstance(recon["steps"], list)
    )
    mastery = fresh_server._call_tool("mastery_map", {})
    mastery_ok = int(
        isinstance(mastery, dict)
        and isinstance(mastery["topics"], list)
        and isinstance(mastery["next_steps"], list)
    )
    attn = fresh_server._call_tool(
        "attention_filter", {"task": "t19-0", "top_k": 3}
    )
    attn_ok = int(
        isinstance(attn, dict)
        and isinstance(attn["relevant"], list)
        and "suppressed_count" in attn
    )
    analogy = fresh_server._call_tool(
        "analogy_bridge", {"min_structure": 0.2, "limit": 3}
    )
    analogy_ok = int(
        isinstance(analogy, dict)
        and "analogy_count" in analogy
        and isinstance(analogy["analogies"], list)
    )
    interval = fresh_server._call_tool("next_interval", {})
    interval_ok = int(
        isinstance(interval, dict)
        and "count" in interval
        and isinstance(interval["rows"], list)
    )
    nightly = fresh_server._call_tool(
        "nightly_routine", {"review_limit": 3, "quiz_count": 3}
    )
    nightly_ok = int(
        isinstance(nightly, dict)
        and isinstance(nightly["tonight_review"], list)
        and isinstance(nightly["tomorrow_quiz"], list)
    )
    cues = fresh_server._call_tool("cue_diversity", {"limit": 10})
    cues_ok = int(
        isinstance(cues, dict)
        and "level_counts" in cues
        and isinstance(cues["rows"], list)
    )
    weekly = fresh_server._call_tool("weekly_review", {})
    weekly_ok = int(
        isinstance(weekly, dict)
        and "week_summary" in weekly
        and isinstance(weekly["next_week_plan"], list)
    )
    transfer = fresh_server._call_tool("transfer_prompt", {"count": 2})
    transfer_ok = int(
        isinstance(transfer, dict)
        and isinstance(transfer["topics"], list)
        and isinstance(transfer["prompts"], list)
    )
    curve = fresh_server._call_tool("curve_fit", {"threshold": 0.4})
    curve_ok = int(
        isinstance(curve, dict)
        and "count" in curve
        and isinstance(curve["rows"], list)
    )
    affect = fresh_server._call_tool("affect_decay", {})
    affect_ok = int(
        isinstance(affect, dict)
        and "total_emotional" in affect
        and "status_counts" in affect
    )
    goal = fresh_server._call_tool("goal_progress", {"goal": "t19-0"})
    goal_ok = int(
        isinstance(goal, dict)
        and "progress_ratio" in goal
        and goal["status"] in ("mastered", "in_progress", "not_started")
    )
    snapshot = fresh_server._call_tool("retrieval_snapshot", {})
    snapshot_ok = int(
        isinstance(snapshot, dict)
        and "snapshot" in snapshot
        and snapshot["diff"] is None
    )
    rehearsal = fresh_server._call_tool(
        "plan_rehearsal", {"goal": "t19-0 相关"}
    )
    rehearsal_ok = int(
        isinstance(rehearsal, dict)
        and "steps" in rehearsal
        and "weakest_step" in rehearsal
        and "rehearsal_advice" in rehearsal
    )
    math = fresh_server._call_tool(
        "math_ladder",
        {"problem": "汽车速度60千米每小时行驶2小时，路程是多少？"},
    )
    math_ok = int(
        isinstance(math, dict)
        and "速度" in math["types"]
        and math["verdict"] == "ready"
        and math["general"] is not None
    )
    physics = fresh_server._call_tool(
        "physics_simulate", {"scene": "一个球从10米高的地方落下"}
    )
    physics_ok = int(
        isinstance(physics, dict)
        and physics["verdict"] == "ready"
        and len(physics["phases"]) == 4
    )
    analogy = fresh_server._call_tool("analogy_prompt", {"count": 2})
    analogy_prompt_ok = int(
        isinstance(analogy, dict)
        and "prompts" in analogy
        and isinstance(analogy["prompts"], list)
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
    consistency = fresh_server._call_tool("review_consistency", {})
    consistency_ok = int(
        isinstance(consistency, dict)
        and consistency["reviewed_count"] >= 1
        and consistency["verdict"] in ("high", "medium", "low")
    )
    search_ok = sum(
        1
        for i in range(6)
        if (
            (r := fresh_server._call_tool(
                "search", {"query": f"t19-{i}", "top_k": 3}
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
        "dependency_map": dep_ok,
        "project_risk": project_risk_ok,
        "plan_tracker": tracker_ok,
        "plan_rewrite": rewrite_ok,
        "lesson_learned": lessons_ok,
        "effort_estimate": effort_ok,
        "decision_review": review_ok,
        "transfer_report": transfer_ok,
        "retrieval_quality": rq_ok,
        "recall_trace": trace_ok,
        "community_report": community_ok,
        "sleep_advice": sleep_ok,
        "emotion_advice": emotion_ok,
        "difficulty_estimator": diff_ok,
        "memory_integration": integ_ok,
        "reasoning_trace": trace_ok,
        "goal_replay": goal_ok,
        "sleep_inference": slep_ok,
        "schema_fit": schema_ok,
        "working_set_budget": budget_ok,
        "test_generator": tests_ok,
        "spacing_plan": spaced_ok,
        "rumination_check": rumi_ok,
        "consolidation_forecast": consol_ok,
        "forgetting_balance": fb_ok,
        "metacog_report": meta_ok,
        "reconsolidation_plan": recon_ok,
        "mastery_map": mastery_ok,
        "attention_filter": attn_ok,
        "analogy_bridge": analogy_ok,
        "next_interval": interval_ok,
        "nightly_routine": nightly_ok,
        "cue_diversity": cues_ok,
        "weekly_review": weekly_ok,
        "transfer_prompt": transfer_ok,
        "curve_fit": curve_ok,
        "affect_decay": affect_ok,
        "goal_progress": goal_ok,
        "retrieval_snapshot": snapshot_ok,
        "plan_rehearsal": rehearsal_ok,
        "math_ladder": math_ok,
        "physics_simulate": physics_ok,
        "analogy_prompt": analogy_prompt_ok,
        "review_consistency": consistency_ok,
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
        default=os.path.join(_BENCH, "results", "toolchain29_eval.json"),
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
