"""MCP tool handler mixin: the 130 @_tool methods.

Kept separate from the transport/server code so each tool is a plain
method on :class:`MCPHandlersMixin`; ``MCPServer`` inherits it.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .embedding import NGramEmbedder
from .mcp_registry import _tool
from .types import MemoryKind, SourceRecord, SourceType


def _kind(value: Any) -> MemoryKind | None:
    if value is None:
        return None
    return MemoryKind(value)


def _bounded(args: dict[str, Any], key: str, default: int, lo: int, hi: int) -> int:
    """Read an int arg clamped to [lo, hi]; malformed/absent -> default."""
# mypy: disable-error-code="attr-defined"
    try:
        value = int(args.get(key, default))
    except (TypeError, ValueError):
        value = default
    return max(lo, min(hi, value))


def _dt(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        raise ValueError(
            f"{field} 需要 ISO 格式时间（如 2026-08-11T18:00:00），"
            f"收到：{value!r}"
        )
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _source_type(value: Any) -> SourceType:
    try:
        return SourceType(value)
    except ValueError:
        return SourceType.USER


class MCPHandlersMixin:
    @_tool("remember")
    def _tool_remember(self, args: dict[str, Any]) -> Any:
        item = self.engine.remember(
            args["content"],
            kind=_kind(args.get("kind")) or MemoryKind.EPISODIC,
            source=SourceRecord(
                origin=_source_type(args.get("source", SourceType.USER.value))
            ),
            cues=args.get("cues"),
            context=args.get("context"),
            affect=args.get("affect"),
            importance=args.get("importance"),
            confidence=(
                float(args["confidence"])
                if args.get("confidence") is not None
                else 1.0
            ),
            evidence_count=(
                int(args["evidence_count"])
                if args.get("evidence_count") is not None
                else 1
            ),
        )
        return {
            "id": item.id,
            "kind": item.kind.value,
            "content": item.content,
            "cues": item.cues,
            "importance": item.importance,
        }

    @_tool("remember_turn")
    def _tool_remember_turn(self, args: dict[str, Any]) -> Any:
        return self.engine.remember_turn(
            args["text"],
            max_segments=_bounded(args, "max_segments", 4, 1, 50),
        )

    @_tool("recall")
    def _tool_recall(self, args: dict[str, Any]) -> Any:
        embedder = (
            NGramEmbedder()
            if args.get("embedder") == "ngram"
            else None
        )
        results = self.engine.recall(
            args["query"],
            kind=_kind(args.get("kind")),
            top_k=_bounded(args, "top_k", 5, 1, 500),
            context=args.get("context"),
            embedder=embedder,
        )
        return [
            {
                "id": r.item.id,
                "score": round(r.score, 3),
                "kind": r.item.kind.value,
                "content": r.item.content,
                "confidence": r.item.confidence,
            }
            for r in results
        ]

    @_tool("search_batch")
    def _tool_search_batch(self, args: dict[str, Any]) -> Any:
        return self.engine.search_batch(
            args["queries"],
            kind=_kind(args.get("kind")),
            top_k=_bounded(args, "top_k", 3, 1, 500),
        )

    @_tool("sleep")
    def _tool_sleep(self, args: dict[str, Any]) -> Any:
        report = self.engine.sleep()
        return {
            "summary": report.summary(),
            "promoted": len(report.promoted),
            "pruned": len(report.recycled),
            "reflected": len(report.reflected),
            "conflicts": len(report.conflicts),
        }

    @_tool("check")
    def _tool_check(self, args: dict[str, Any]) -> Any:
        check = self.engine.check(args["query"], top_k=_bounded(args, "top_k", 3, 1, 500))
        return {
            "items": [
                {
                    "content": item.content,
                    "label": label.value,
                    "confidence": value,
                }
                for item, label, value in check.items
            ],
            "contradictions": len(check.contradictions),
            "gaps": check.gaps,
            "blocked": [b.content for b in check.blocked],
        }

    @_tool("update")
    def _tool_update(self, args: dict[str, Any]) -> Any:
        item = self.engine.update(
            args["memory_id"],
            content=args.get("content"),
            importance=args.get("importance"),
            confidence=args.get("confidence"),
            cues=args.get("cues"),
        )
        if item is None:
            raise ValueError(f"no memory with id {args['memory_id']}")
        return {
            "id": item.id,
            "content": item.content,
            "revision_count": item.revision_count,
            "confidence": item.confidence,
        }

    @_tool("forget")
    def _tool_forget(self, args: dict[str, Any]) -> Any:
        return {"ok": self.engine.forget(args["memory_id"])}

    @_tool("restore")
    def _tool_restore(self, args: dict[str, Any]) -> Any:
        return {"ok": self.engine.restore(args["memory_id"])}

    @_tool("stats")
    def _tool_stats(self, args: dict[str, Any]) -> Any:
        return self.engine.stats()

    @_tool("calibrate_decay")
    def _tool_calibrate_decay(self, args: dict[str, Any]) -> Any:
        return self.engine.calibrate_decay_rate()

    @_tool("rebuild_vectors")
    def _tool_rebuild_vectors(self, args: dict[str, Any]) -> Any:
        return {"rebuilt": self.engine.rebuild_missing_vectors()}

    @_tool("working_set")
    def _tool_working_set(self, args: dict[str, Any]) -> Any:
        return [
            {
                "id": item.id,
                "content": item.content,
                "last_access_at": (
                    item.last_access_at.isoformat()
                    if item.last_access_at
                    else None
                ),
            }
            for item in self.engine.working_set(limit=_bounded(args, "limit", 8, 1, 5000))
        ]

    @_tool("review_due")
    def _tool_review_due(self, args: dict[str, Any]) -> Any:
        return [
            {
                "id": item.id,
                "content": item.content,
                "retrievability": round(
                    self.engine.curve.retrievability(item), 3
                ),
            }
            for item in self.engine.review_due(
                limit=_bounded(args, "limit", 10, 1, 5000),
                desirable_difficulty=bool(
                    args.get("desirable_difficulty", False)
                ),
                difficulty_target=float(
                    args.get("difficulty_target", 0.45)
                ),
            )
        ]

    @_tool("review")
    def _tool_review(self, args: dict[str, Any]) -> Any:
        item = self.engine.review(
            args["memory_id"], success=bool(args.get("success", True))
        )
        if item is None:
            raise ValueError(f"no memory with id {args['memory_id']}")
        return {
            "id": item.id,
            "review_streak": item.review_streak,
            "retrieval_successes": item.retrieval_successes,
            "retrieval_failures": item.retrieval_failures,
        }

    @_tool("plan")
    def _tool_plan(self, args: dict[str, Any]) -> Any:
        results = self.engine.plan_for_goal(
            args["goal"],
            top_k=(
                _bounded(args, "top_k", 8, 1, 500)
                if args.get("top_k") is not None
                else None
            ),
            effort=args.get("effort"),
        )
        return [
            {
                "content": r.item.content,
                "score": round(r.score, 3),
                "reasons": r.reasons,
            }
            for r in results
        ]

    @_tool("reason")
    def _tool_reason(self, args: dict[str, Any]) -> Any:
        results = self.engine.recall_reasoning(
            args["query"], top_k=_bounded(args, "top_k", 8, 1, 500)
        )
        return [
            {
                "content": r.item.content,
                "score": round(r.score, 3),
                "reasons": r.reasons,
            }
            for r in results
        ]

    @_tool("record_outcome")
    def _tool_record_outcome(self, args: dict[str, Any]) -> Any:
        item = self.engine.record_outcome(
            args["goal"],
            args["step"],
            success=bool(args["success"]),
            note=args.get("note"),
        )
        return {
            "id": item.id,
            "content": item.content,
            "evidence_count": item.evidence_count,
        }

    @_tool("replan")
    def _tool_replan(self, args: dict[str, Any]) -> Any:
        results = self.engine.replan(
            args["goal"],
            args["failed_step"],
            top_k=(
                _bounded(args, "top_k", 8, 1, 500)
                if args.get("top_k") is not None
                else None
            ),
        )
        return [
            {
                "content": r.item.content,
                "score": round(r.score, 3),
                "reasons": r.reasons,
            }
            for r in results
        ]

    @_tool("predict_step")
    def _tool_predict_step(self, args: dict[str, Any]) -> Any:
        return self.engine.predict_step(args["step"])

    @_tool("sleep_replay")
    def _tool_sleep_replay(self, args: dict[str, Any]) -> Any:
        return self.engine.sleep_replay()

    @_tool("search")
    def _tool_search(self, args: dict[str, Any]) -> Any:
        results = self.engine.recall(
            args["query"],
            top_k=_bounded(args, "top_k", 5, 1, 500),
            context=args.get("context") or None,
        )
        return [
            {
                "id": result.item.id,
                "content": result.item.content,
                "score": round(result.score, 4),
                "confident": result.confident,
                "reasons": result.reasons,
            }
            for result in results
        ]

    @_tool("list_conflicts")
    def _tool_list_conflicts(self, args: dict[str, Any]) -> Any:
        conflicts = self.engine.consolidator.detect_conflicts()
        return [
            {
                "a_id": conflict.a.id,
                "a": conflict.a.content,
                "b_id": conflict.b.id,
                "b": conflict.b.content,
                "reason": conflict.reason,
            }
            for conflict in conflicts
        ]

    @_tool("conflict_advice")
    def _tool_conflict_advice(self, args: dict[str, Any]) -> Any:
        return self.engine.conflict_advice(
            limit=_bounded(args, "limit", 10, 1, 5000)
        )

    @_tool("memory_status")
    def _tool_memory_status(self, args: dict[str, Any]) -> Any:
        return self.engine.memory_status()

    @_tool("review_batch")
    def _tool_review_batch(self, args: dict[str, Any]) -> Any:
        return self.engine.review_batch(args["answers"])

    @_tool("export_memories")
    def _tool_export_memories(self, args: dict[str, Any]) -> Any:
        return self.engine.export_memories()

    @_tool("import_memories")
    def _tool_import_memories(self, args: dict[str, Any]) -> Any:
        return self.engine.import_memories(args["payload"])

    @_tool("practice_session")
    def _tool_practice_session(self, args: dict[str, Any]) -> Any:
        return self.engine.practice_session(
            args["answers"],
            limit=_bounded(args, "limit", 5, 1, 5000),
        )

    @_tool("sleep_and_plan")
    def _tool_sleep_and_plan(self, args: dict[str, Any]) -> Any:
        return self.engine.sleep_and_plan(
            days=_bounded(args, "days", 7, 1, 3650)
        )

    @_tool("memory_audit")
    def _tool_memory_audit(self, args: dict[str, Any]) -> Any:
        return self.engine.memory_audit()

    @_tool("dedupe_memories")
    def _tool_dedupe_memories(self, args: dict[str, Any]) -> Any:
        return self.engine.dedupe_memories()

    @_tool("resolve_conflicts")
    def _tool_resolve_conflicts(self, args: dict[str, Any]) -> Any:
        return self.engine.resolve_conflicts()

    @_tool("review_load")
    def _tool_review_load(self, args: dict[str, Any]) -> Any:
        return self.engine.review_load(
            days=_bounded(args, "days", 7, 1, 3650)
        )

    @_tool("tag_memories")
    def _tool_tag_memories(self, args: dict[str, Any]) -> Any:
        return self.engine.tag_memories(
            args["memory_ids"],
            args["tags"],
            action=args.get("action", "add"),
        )

    @_tool("recall_log")
    def _tool_recall_log(self, args: dict[str, Any]) -> Any:
        return self.engine.get_recall_log(
            limit=_bounded(args, "limit", 50, 1, 5000)
        )

    @_tool("cleanup_preview")
    def _tool_cleanup_preview(self, args: dict[str, Any]) -> Any:
        return self.engine.cleanup_preview(
            limit=_bounded(args, "limit", 100, 1, 5000)
        )

    @_tool("similarity_report")
    def _tool_similarity_report(self, args: dict[str, Any]) -> Any:
        return self.engine.similarity_report(
            threshold=float(args.get("threshold", 0.6)),
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("association_report")
    def _tool_association_report(self, args: dict[str, Any]) -> Any:
        return self.engine.association_report(
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("intent_remember")
    def _tool_intent_remember(self, args: dict[str, Any]) -> Any:

        return self.engine.remember_intent(
            args["content"],
            _dt(args["due_at"], "due_at"),
            context_cue=args.get("context_cue"),
            importance=float(args.get("importance", 0.5)),
        )

    @_tool("intent_due")
    def _tool_intent_due(self, args: dict[str, Any]) -> Any:
        return self.engine.intent_due(
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("intent_complete")
    def _tool_intent_complete(self, args: dict[str, Any]) -> Any:
        return self.engine.complete_intent(args["intent_id"])

    @_tool("intent_cancel")
    def _tool_intent_cancel(self, args: dict[str, Any]) -> Any:
        return self.engine.cancel_intent(args["intent_id"])

    @_tool("intent_report")
    def _tool_intent_report(self, args: dict[str, Any]) -> Any:
        return self.engine.intent_report()

    @_tool("retrieval_assist")
    def _tool_retrieval_assist(self, args: dict[str, Any]) -> Any:
        return self.engine.retrieval_assist(
            args["query"],
            limit=_bounded(args, "limit", 8, 1, 5000),
        )

    @_tool("schema_report")
    def _tool_schema_report(self, args: dict[str, Any]) -> Any:
        return self.engine.schema_report(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("suppress_memories")
    def _tool_suppress_memories(self, args: dict[str, Any]) -> Any:
        return self.engine.suppress_memories(args["memory_ids"])

    @_tool("unsuppress_memories")
    def _tool_unsuppress_memories(self, args: dict[str, Any]) -> Any:
        return self.engine.unsuppress_memories(args["memory_ids"])

    @_tool("suppressed_report")
    def _tool_suppressed_report(self, args: dict[str, Any]) -> Any:
        return self.engine.suppressed_report()

    @_tool("timeline_report")
    def _tool_timeline_report(self, args: dict[str, Any]) -> Any:

        return self.engine.timeline_report(
            start=(
                _dt(args["start"], "start")
                if args.get("start")
                else None
            ),
            end=(
                _dt(args["end"], "end")
                if args.get("end")
                else None
            ),
            limit=_bounded(args, "limit", 200, 1, 5000),
        )

    @_tool("recognition_check")
    def _tool_recognition_check(self, args: dict[str, Any]) -> Any:
        return self.engine.recognition_check(
            args["query"], args["memory_id"]
        )

    @_tool("interference_report")
    def _tool_interference_report(self, args: dict[str, Any]) -> Any:
        return self.engine.interference_report(
            shared_cue_min=_bounded(args, "shared_cue_min", 3, 1, 100),
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("life_story")
    def _tool_life_story(self, args: dict[str, Any]) -> Any:
        return self.engine.life_story(
            period_days=_bounded(args, "period_days", 30, 1, 3650),
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("intent_conflicts")
    def _tool_intent_conflicts(self, args: dict[str, Any]) -> Any:
        return self.engine.intent_conflicts(
            time_window_minutes=int(
                args.get("time_window_minutes", 60)
            ),
        )

    @_tool("memory_health")
    def _tool_memory_health(self, args: dict[str, Any]) -> Any:
        return self.engine.memory_health()

    @_tool("memory_map")
    def _tool_memory_map(self, args: dict[str, Any]) -> Any:
        return self.engine.memory_map(
            limit=_bounded(args, "limit", 200, 1, 5000),
            topic_min=_bounded(args, "topic_min", 1, 1, 100),
        )

    @_tool("kg_export")
    def _tool_kg_export(self, args: dict[str, Any]) -> Any:
        return self.engine.kg_export()

    @_tool("learner_profile")
    def _tool_learner_profile(self, args: dict[str, Any]) -> Any:
        return self.engine.learner_profile()

    @_tool("context_pack")
    def _tool_context_pack(self, args: dict[str, Any]) -> Any:
        return self.engine.context_pack(
            args["queries"],
            top_k=_bounded(args, "top_k", 3, 1, 500),
            max_chars=_bounded(args, "max_chars", 1200, 1, 100000),
        )

    @_tool("encoding_quality")
    def _tool_encoding_quality(self, args: dict[str, Any]) -> Any:
        return self.engine.encoding_quality(args["memory_id"])

    @_tool("explain_memory")
    def _tool_explain_memory(self, args: dict[str, Any]) -> Any:
        return self.engine.explain_memory(args["memory_id"])

    @_tool("compare_memories")
    def _tool_compare_memories(self, args: dict[str, Any]) -> Any:
        return self.engine.compare_memories(
            args["id_a"], args["id_b"]
        )

    @_tool("action_queue")
    def _tool_action_queue(self, args: dict[str, Any]) -> Any:
        return self.engine.action_queue(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("summarize_cluster")
    def _tool_summarize_cluster(self, args: dict[str, Any]) -> Any:
        return self.engine.summarize_cluster(args["memory_ids"])

    @_tool("multi_hop_report")
    def _tool_multi_hop_report(self, args: dict[str, Any]) -> Any:
        return self.engine.multi_hop_report(
            args["start_id"],
            depth=_bounded(args, "depth", 2, 1, 20),
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("cramming_plan")
    def _tool_cramming_plan(self, args: dict[str, Any]) -> Any:

        return self.engine.cramming_plan(
            _dt(args["target_at"], "target_at"),
            hours_available=float(args.get("hours_available", 6.0)),
            session_minutes=_bounded(args, "session_minutes", 30, 1, 10080),
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("session_summary")
    def _tool_session_summary(self, args: dict[str, Any]) -> Any:
        return self.engine.session_summary(
            args["memory_ids"],
            compare_limit=_bounded(args, "compare_limit", 20, 1, 1000),
        )

    @_tool("topic_drift_report")
    def _tool_topic_drift_report(self, args: dict[str, Any]) -> Any:
        return self.engine.topic_drift_report(
            period_days=_bounded(args, "period_days", 30, 1, 3650),
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("forgetting_export")
    def _tool_forgetting_export(self, args: dict[str, Any]) -> Any:
        return self.engine.forgetting_export(
            args["memory_id"],
            days=_bounded(args, "days", 30, 1, 3650),
            step_days=_bounded(args, "step_days", 1, 1, 3650),
        )

    @_tool("coverage_report")
    def _tool_coverage_report(self, args: dict[str, Any]) -> Any:
        return self.engine.coverage_report(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("source_calibration")
    def _tool_source_calibration(self, args: dict[str, Any]) -> Any:
        return self.engine.source_calibration()

    @_tool("forgetting_risk")
    def _tool_forgetting_risk(self, args: dict[str, Any]) -> Any:
        return self.engine.forgetting_risk(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("bridge_suggestions")
    def _tool_bridge_suggestions(self, args: dict[str, Any]) -> Any:
        return self.engine.bridge_suggestions(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("plan_quality")
    def _tool_plan_quality(self, args: dict[str, Any]) -> Any:
        return self.engine.plan_quality(
            args["plan"],
            context_memory_ids=args.get("context_memory_ids"),
        )

    @_tool("project_brief")
    def _tool_project_brief(self, args: dict[str, Any]) -> Any:
        return self.engine.project_brief(
            args["title"],
            memory_ids=args.get("memory_ids"),
            limit=_bounded(args, "limit", 8, 1, 5000),
        )

    @_tool("numeric_reasoning")
    def _tool_numeric_reasoning(self, args: dict[str, Any]) -> Any:
        return self.engine.numeric_reasoning(
            args["problem"],
            context_memory_ids=args.get("context_memory_ids"),
        )

    @_tool("plan_support")
    def _tool_plan_support(self, args: dict[str, Any]) -> Any:
        return self.engine.plan_support(
            args["plan"],
            top_k=_bounded(args, "top_k", 3, 1, 500),
        )

    @_tool("dependency_map")
    def _tool_dependency_map(self, args: dict[str, Any]) -> Any:
        return self.engine.dependency_map(args["plan"])

    @_tool("project_risk")
    def _tool_project_risk(self, args: dict[str, Any]) -> Any:
        return self.engine.project_risk(
            memory_ids=args.get("memory_ids"),
            compare_limit=_bounded(args, "compare_limit", 20, 1, 1000),
        )

    @_tool("plan_tracker")
    def _tool_plan_tracker(self, args: dict[str, Any]) -> Any:
        return self.engine.plan_tracker(
            args["plan"],
            statuses=args.get("statuses"),
        )

    @_tool("plan_rewrite")
    def _tool_plan_rewrite(self, args: dict[str, Any]) -> Any:
        return self.engine.plan_rewrite(args["plan"])

    @_tool("lesson_learned")
    def _tool_lesson_learned(self, args: dict[str, Any]) -> Any:
        return self.engine.lesson_learned(
            memory_ids=args.get("memory_ids"),
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("effort_estimate")
    def _tool_effort_estimate(self, args: dict[str, Any]) -> Any:
        return self.engine.effort_estimate(
            args["plan"],
            base_hours=float(args.get("base_hours", 2.0)),
        )

    @_tool("decision_review")
    def _tool_decision_review(self, args: dict[str, Any]) -> Any:
        return self.engine.decision_review(
            args["plan"],
            args["results"],
        )

    @_tool("transfer_report")
    def _tool_transfer_report(self, args: dict[str, Any]) -> Any:
        return self.engine.transfer_report(
            args["plan"],
            lessons_memory_ids=args.get("lessons_memory_ids"),
        )

    @_tool("retrieval_quality")
    def _tool_retrieval_quality(self, args: dict[str, Any]) -> Any:
        return self.engine.retrieval_quality(
            queries=args.get("queries"),
            top_k=_bounded(args, "top_k", 5, 1, 500),
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("recall_trace")
    def _tool_recall_trace(self, args: dict[str, Any]) -> Any:
        return self.engine.recall_trace(
            args["query"],
            top_k=_bounded(args, "top_k", 5, 1, 500),
        )

    @_tool("community_report")
    def _tool_community_report(self, args: dict[str, Any]) -> Any:
        return self.engine.community_report(
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("sleep_advice")
    def _tool_sleep_advice(self, args: dict[str, Any]) -> Any:
        return self.engine.sleep_advice()

    @_tool("emotion_advice")
    def _tool_emotion_advice(self, args: dict[str, Any]) -> Any:
        return self.engine.emotion_advice(
            memory_ids=args.get("memory_ids"),
        )

    @_tool("difficulty_estimator")
    def _tool_difficulty_estimator(self, args: dict[str, Any]) -> Any:
        return self.engine.difficulty_estimator(
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("memory_integration")
    def _tool_memory_integration(self, args: dict[str, Any]) -> Any:
        return self.engine.memory_integration(
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("reasoning_trace")
    def _tool_reasoning_trace(self, args: dict[str, Any]) -> Any:
        return self.engine.reasoning_trace(
            problem=str(args.get("problem", "")),
            topic=args.get("topic"),
            top_k=_bounded(args, "top_k", 4, 1, 500),
            store_conclusion=bool(
                args.get("store_conclusion", True)
            ),
        )

    @_tool("goal_replay")
    def _tool_goal_replay(self, args: dict[str, Any]) -> Any:
        return self.engine.goal_replay(
            goal=str(args.get("goal", "")),
            top_k=_bounded(args, "top_k", 5, 1, 500),
        )

    @_tool("sleep_inference")
    def _tool_sleep_inference(self, args: dict[str, Any]) -> Any:
        return self.engine.sleep_inference(
            limit=_bounded(args, "limit", 5, 1, 5000),
        )

    @_tool("schema_fit")
    def _tool_schema_fit(self, args: dict[str, Any]) -> Any:
        return self.engine.schema_fit(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("working_set_budget")
    def _tool_working_set_budget(self, args: dict[str, Any]) -> Any:
        return self.engine.working_set_budget(
            limit=_bounded(args, "limit", 8, 1, 5000),
            capacity=_bounded(args, "capacity", 7, 1, 1000),
            optimal=_bounded(args, "optimal", 4, 1, 100),
        )

    @_tool("test_generator")
    def _tool_test_generator(self, args: dict[str, Any]) -> Any:
        return self.engine.test_generator(
            topic=args.get("topic"),
            memory_ids=args.get("memory_ids"),
            count=_bounded(args, "count", 4, 1, 100),
        )

    @_tool("spacing_plan")
    def _tool_spacing_plan(self, args: dict[str, Any]) -> Any:
        return self.engine.spacing_plan(
            days=_bounded(args, "days", 7, 1, 3650),
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("rumination_check")
    def _tool_rumination_check(self, args: dict[str, Any]) -> Any:
        return self.engine.rumination_check(
            access_threshold=_bounded(args, "access_threshold", 5, 0, 1000000),
        )

    @_tool("consolidation_forecast")
    def _tool_consolidation_forecast(self, args: dict[str, Any]) -> Any:
        return self.engine.consolidation_forecast(
            limit=_bounded(args, "limit", 5, 1, 5000),
        )

    @_tool("forgetting_balance")
    def _tool_forgetting_balance(self, args: dict[str, Any]) -> Any:
        return self.engine.forgetting_balance(
            imbalance_ratio=float(
                args.get("imbalance_ratio", 3.0)
            ),
            limit=_bounded(args, "limit", 10, 1, 5000),
        )

    @_tool("metacog_report")
    def _tool_metacog_report(self, args: dict[str, Any]) -> Any:
        return self.engine.metacog_report(
            min_attempts=_bounded(args, "min_attempts", 3, 1, 100),
        )

    @_tool("reconsolidation_plan")
    def _tool_reconsolidation_plan(self, args: dict[str, Any]) -> Any:
        return self.engine.reconsolidation_plan(
            memory_id=str(args.get("memory_id", "")),
        )

    @_tool("mastery_map")
    def _tool_mastery_map(self, args: dict[str, Any]) -> Any:
        return self.engine.mastery_map(
            threshold=float(args.get("threshold", 0.5)),
            min_attempts=_bounded(args, "min_attempts", 3, 1, 100),
        )

    @_tool("attention_filter")
    def _tool_attention_filter(self, args: dict[str, Any]) -> Any:
        return self.engine.attention_filter(
            task=str(args.get("task", "")),
            top_k=_bounded(args, "top_k", 5, 1, 500),
        )

    @_tool("analogy_bridge")
    def _tool_analogy_bridge(self, args: dict[str, Any]) -> Any:
        return self.engine.analogy_bridge(
            min_structure=float(args.get("min_structure", 0.3)),
            limit=_bounded(args, "limit", 5, 1, 5000),
        )

    @_tool("next_interval")
    def _tool_next_interval(self, args: dict[str, Any]) -> Any:
        return self.engine.next_interval(
            memory_id=args.get("memory_id"),
        )

    @_tool("nightly_routine")
    def _tool_nightly_routine(self, args: dict[str, Any]) -> Any:
        return self.engine.nightly_routine(
            review_limit=_bounded(args, "review_limit", 3, 1, 500),
            quiz_count=_bounded(args, "quiz_count", 3, 1, 100),
        )

    @_tool("cue_diversity")
    def _tool_cue_diversity(self, args: dict[str, Any]) -> Any:
        return self.engine.cue_diversity(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("weekly_review")
    def _tool_weekly_review(self, args: dict[str, Any]) -> Any:
        return self.engine.weekly_review()

    @_tool("transfer_prompt")
    def _tool_transfer_prompt(self, args: dict[str, Any]) -> Any:
        return self.engine.transfer_prompt(
            count=_bounded(args, "count", 3, 1, 100),
            min_mastery=float(args.get("min_mastery", 0.7)),
        )

    @_tool("curve_fit")
    def _tool_curve_fit(self, args: dict[str, Any]) -> Any:
        return self.engine.curve_fit(
            memory_id=args.get("memory_id"),
            horizon_days=_bounded(args, "horizon_days", 30, 1, 3650),
            threshold=float(args.get("threshold", 0.4)),
        )

    @_tool("affect_decay")
    def _tool_affect_decay(self, args: dict[str, Any]) -> Any:
        return self.engine.affect_decay(
            limit=_bounded(args, "limit", 20, 1, 5000),
        )

    @_tool("goal_progress")
    def _tool_goal_progress(self, args: dict[str, Any]) -> Any:
        return self.engine.goal_progress(
            goal=str(args.get("goal", "")),
        )

    @_tool("plan_rehearsal")
    def _tool_plan_rehearsal(self, args: dict[str, Any]) -> Any:
        return self.engine.plan_rehearsal(
            goal=str(args.get("goal", "")),
            top_k=args.get("top_k"),
        )

    @_tool("math_ladder")
    def _tool_math_ladder(self, args: dict[str, Any]) -> Any:
        return self.engine.math_ladder(
            problem=str(args.get("problem", "")),
            top_k=_bounded(args, "top_k", 4, 1, 500),
        )

    @_tool("physics_simulate")
    def _tool_physics_simulate(self, args: dict[str, Any]) -> Any:
        return self.engine.physics_simulate(
            scene=str(args.get("scene", "")),
            top_k=_bounded(args, "top_k", 4, 1, 500),
        )

    @_tool("analogy_prompt")
    def _tool_analogy_prompt(self, args: dict[str, Any]) -> Any:
        return self.engine.analogy_prompt(
            topic=args.get("topic"),
            count=_bounded(args, "count", 3, 1, 100),
            min_mastery=float(args.get("min_mastery", 0.7)),
        )

    @_tool("review_consistency")
    def _tool_review_consistency(self, args: dict[str, Any]) -> Any:
        return self.engine.review_consistency()

    @_tool("learning_loop")
    def _tool_learning_loop(self, args: dict[str, Any]) -> Any:
        return self.engine.learning_loop(
            count=_bounded(args, "count", 1, 1, 100),
        )

    @_tool("agent_learning_session")
    def _tool_agent_learning_session(self, args: dict[str, Any]) -> Any:
        return self.engine.agent_learning_session(
            answers=args.get("answers"),
            count=_bounded(args, "count", 1, 1, 100),
        )

    @_tool("concept_cover")
    def _tool_concept_cover(self, args: dict[str, Any]) -> Any:
        return self.engine.concept_cover(
            query=str(args.get("query", "")),
            top_k=_bounded(args, "top_k", 4, 1, 500),
        )

    @_tool("temporal_anchor")
    def _tool_temporal_anchor(self, args: dict[str, Any]) -> Any:
        return self.engine.temporal_anchor(
            query=str(args.get("query", "")),
            top_k=_bounded(args, "top_k", 4, 1, 500),
        )

    @_tool("retrieval_snapshot")
    def _tool_retrieval_snapshot(self, args: dict[str, Any]) -> Any:
        return self.engine.retrieval_snapshot(
            previous=args.get("previous"),
        )

    @_tool("practice_due")
    def _tool_practice_due(self, args: dict[str, Any]) -> Any:
        kind_value = args.get("kind")

        return self.engine.practice_due(
            limit=_bounded(args, "limit", 5, 1, 5000),
            desirable_difficulty=bool(
                args.get("desirable_difficulty", True)
            ),
            min_gap_hours=float(args.get("min_gap_hours", 24.0)),
            adaptive_gap=bool(args.get("adaptive_gap", True)),
            interleave=bool(args.get("interleave", True)),
            vary_cues=bool(args.get("vary_cues", True)),
            arousal_priority=bool(args.get("arousal_priority", True)),
            fresh_priority=bool(args.get("fresh_priority", False)),
            kind=(
                MemoryKind(kind_value)
                if kind_value in ("semantic", "episodic")
                else None
            ),
        )

    @_tool("practice_answer")
    def _tool_practice_answer(self, args: dict[str, Any]) -> Any:
        return self.engine.practice_answer(
            args["memory_id"],
            args["attempt"],
            suppress_competitors=bool(
                args.get("suppress_competitors", True)
            ),
            generation_bonus=bool(
                args.get("generation_bonus", True)
            ),
        )

    @_tool("practice_report")
    def _tool_practice_report(self, args: dict[str, Any]) -> Any:
        return self.engine.practice_report(args["answers"])

    @_tool("practice_plan")
    def _tool_practice_plan(self, args: dict[str, Any]) -> Any:
        return self.engine.practice_plan(
            limit=_bounded(args, "limit", 5, 1, 5000)
        )

    @_tool("practice_forecast")
    def _tool_practice_forecast(self, args: dict[str, Any]) -> Any:
        return self.engine.practice_forecast(
            days=_bounded(args, "days", 7, 1, 3650)
        )


__all__ = ["MCPHandlersMixin"]
