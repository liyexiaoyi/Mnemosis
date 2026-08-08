"""Minimal stdio MCP server for Mnemosis.

Implemented on `stdlib` only (JSON-RPC 2.0 over newline-delimited stdio), so
it follows the project's zero-dependency rule and can be wired into Claude
Code, Codex, or any MCP client:

    mnemosis mcp --db memory.db
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .engine import MemoryEngine
from .embedding import NGramEmbedder
from .types import MemoryKind, SourceRecord, SourceType

PROTOCOL_VERSION = "2025-03-26"


def _kind(value: Any) -> MemoryKind | None:
    if value is None:
        return None
    return MemoryKind(value)


class MCPServer:
    def __init__(self, engine: MemoryEngine | None = None) -> None:
        self.engine = engine or MemoryEngine()
        self._tools = [
            {
                "name": "remember",
                "description": "Store a memory (episodic or semantic).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "kind": {
                            "type": "string",
                            "enum": ["episodic", "semantic"],
                        },
                        "cues": {"type": "array", "items": {"type": "string"}},
                        "context": {"type": "string"},
                        "affect": {
                            "type": "string",
                            "enum": [
                                "positive",
                                "negative",
                                "arousing",
                                "mixed",
                                "neutral",
                            ],
                        },
                        "importance": {"type": "number"},
                        "confidence": {"type": "number"},
                        "evidence_count": {"type": "integer"},
                    },
                    "required": ["content"],
                },
            },
            {
                "name": "recall",
                "description": "Recall memories matching a query.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                        "kind": {
                            "type": "string",
                            "enum": ["episodic", "semantic"],
                        },
                        "context": {"type": "string"},
                        "embedder": {"type": "string", "enum": ["ngram"]},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "search_batch",
                "description": (
                    "Run several recall queries in one call; returns one "
                    "result group per query in input order (single MCP "
                    "round trip for a whole question list)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "top_k": {"type": "integer"},
                        "kind": {
                            "type": "string",
                            "enum": ["episodic", "semantic"],
                        },
                    },
                    "required": ["queries"],
                },
            },
            {
                "name": "sleep",
                "description": "Run sleep consolidation (promote, prune, reflect, conflicts).",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "check",
                "description": "Metacognitive check: confidence, contradictions, gaps, blocked.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "update",
                "description": "Revise a memory (reconsolidation).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "content": {"type": "string"},
                        "importance": {"type": "number"},
                        "confidence": {"type": "number"},
                        "cues": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["memory_id"],
                },
            },
            {
                "name": "forget",
                "description": "Move a memory to the recycle bin.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"memory_id": {"type": "string"}},
                    "required": ["memory_id"],
                },
            },
            {
                "name": "restore",
                "description": "Restore a memory from the recycle bin.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"memory_id": {"type": "string"}},
                    "required": ["memory_id"],
                },
            },
            {
                "name": "stats",
                "description": "Memory statistics.",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "working_set",
                "description": "Recently used memories for prompt injection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
            },
            {
                "name": "review_due",
                "description": (
                    "List memories due for spaced review; optionally prefer "
                    "desirable-difficulty items (hard but likely to succeed)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                        "desirable_difficulty": {"type": "boolean"},
                        "difficulty_target": {"type": "number"},
                    },
                },
            },
            {
                "name": "review",
                "description": "Record a spaced-repetition outcome (success/fail).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "success": {"type": "boolean"},
                    },
                    "required": ["memory_id"],
                },
            },
            {
                "name": "plan",
                "description": (
                    "Agent planning: turn a goal into an ordered step plan, "
                    "reusing the person's own past steps or a referenced "
                    "person's steps as an analogical template."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "top_k": {"type": "integer"},
                        "effort": {
                            "type": "string",
                            "enum": ["low", "medium", "high"],
                            "description": (
                                "Planning depth: low (fast, 6 items, no "
                                "outcome rerank), medium (8, rerank), "
                                "high (14, rerank). Default: auto."
                            ),
                        },
                    },
                    "required": ["goal"],
                },
            },
            {
                "name": "reason",
                "description": (
                    "Reasoning recall: assemble the full premise pack for a "
                    "math / compare / transitive question."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "record_outcome",
                "description": (
                    "Record an execution outcome (success/fail + note) for "
                    "an agent project step (evidence accumulation)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "step": {"type": "string"},
                        "success": {"type": "boolean"},
                        "note": {"type": "string"},
                    },
                    "required": ["goal", "step", "success"],
                },
            },
            {
                "name": "replan",
                "description": (
                    "Re-plan after a failed step: move the failing person's "
                    "step to the end (avoided), keep successful "
                    "alternatives, and store the re-planning decision."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "failed_step": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["goal", "failed_step"],
                },
            },
            {
                "name": "predict_step",
                "description": (
                    "Predict a step's success probability from its outcome "
                    "history (prediction-error updated records)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {"step": {"type": "string"}},
                    "required": ["step"],
                },
            },
            {
                "name": "sleep_replay",
                "description": (
                    "Sleep replay: strengthen surprising outcome records "
                    "and consolidate each step's experience into a "
                    "'历史成功率' summary."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "search",
                "description": (
                    "Retrieve memories for a query: returns the top-k "
                    "matches with content, score, confidence flag and "
                    "reasons (context-dependent recall and all retrieval "
                    "mechanisms apply)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "top_k": {"type": "integer"},
                        "context": {"type": "string"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "list_conflicts",
                "description": (
                    "Return active memory conflicts: same cue, both "
                    "confident, different content. Agents can use this to "
                    "spot contradictions before answering."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "memory_status",
                "description": (
                    "Return a memory-health snapshot: active counts by "
                    "kind, average strength/importance, how many memories "
                    "are due right now, and how many conflicts exist."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "review_batch",
                "description": (
                    "Apply a batch of spaced-repetition outcomes: each "
                    "answer is {id, success}; returns the adaptive scheduler "
                    "state (streak, next review) for every card."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "answers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "success": {"type": "boolean"},
                                },
                                "required": ["id"],
                            },
                        }
                    },
                    "required": ["answers"],
                },
            },
            {
                "name": "export_memories",
                "description": (
                    "Export all active memories as a portable JSON payload "
                    "(versioned, includes retrieval stats)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "import_memories",
                "description": (
                    "Import memories from an export payload; returns the "
                    "number imported."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "payload": {"type": "object"},
                    },
                    "required": ["payload"],
                },
            },
            {
                "name": "practice_session",
                "description": (
                    "Run one complete practice session: returns the coming "
                    "session plan plus the scored report for the answers "
                    "(difficulty and next-review suggestions)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                        "answers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "attempt": {"type": "string"},
                                },
                                "required": ["id"],
                            },
                        },
                    },
                    "required": ["answers"],
                },
            },
            {
                "name": "sleep_and_plan",
                "description": (
                    "Run the full sleep cycle, then return the consolidation "
                    "summary, weak-important replay count, and refreshed "
                    "practice plan/forecast."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer"},
                    },
                },
            },
            {
                "name": "memory_audit",
                "description": (
                    "Deep lifecycle audit: active/recycled counts, revised "
                    "and emotional traces, conflicts, due now, average "
                    "retrievability and importance."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "dedupe_memories",
                "description": (
                    "Merge near-duplicate traces on demand; returns how "
                    "many duplicates were merged."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "resolve_conflicts",
                "description": (
                    "Resolve memory conflicts on demand: lopsided-evidence "
                    "conflicts retire the stale trace, balanced ones lose "
                    "confidence (accommodation + REM-style resolution)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "review_load",
                "description": (
                    "Estimate upcoming review pressure: due now, overdue, "
                    "due within N days, weak traces, and a weighted load "
                    "index."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer"},
                    },
                },
            },
            {
                "name": "tag_memories",
                "description": (
                    "Add or remove tags (cues) on memories in bulk; tags are "
                    "first-class retrieval cues."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "action": {"type": "string",
                                   "enum": ["add", "remove"]},
                    },
                    "required": ["memory_ids", "tags"],
                },
            },
            {
                "name": "recall_log",
                "description": (
                    "Return the most recent recall entries (query, top "
                    "result, confidence, timestamp) as a bounded audit log."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "cleanup_preview",
                "description": (
                    "Preview which episodic traces the sleep prune pass "
                    "would recycle (unimportant, never accessed, old) - "
                    "without deleting anything."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "similarity_report",
                "description": (
                    "Find confusable memory pairs by content-token overlap "
                    "(near-duplicates or pairs needing better separation)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "threshold": {"type": "number"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "association_report",
                "description": (
                    "Summarize the memory association network: total "
                    "links, connected/isolated memories, average links and "
                    "the most-connected memories (spreading activation)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "intent_remember",
                "description": (
                    "Register a future intention (prospective memory): "
                    "content, deadline and optional context cue."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "content": {"type": "string"},
                        "due_at": {"type": "string"},
                        "context_cue": {"type": "string"},
                        "importance": {"type": "number"},
                    },
                    "required": ["content", "due_at"],
                },
            },
            {
                "name": "intent_due",
                "description": (
                    "List active intentions whose deadline has arrived."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "intent_complete",
                "description": "Mark an intention as completed.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "intent_id": {"type": "string"},
                    },
                    "required": ["intent_id"],
                },
            },
            {
                "name": "intent_cancel",
                "description": "Cancel an intention without completing it.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "intent_id": {"type": "string"},
                    },
                    "required": ["intent_id"],
                },
            },
            {
                "name": "intent_report",
                "description": (
                    "Summarize the intention register: active, overdue, "
                    "next upcoming, completed and cancelled counts."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "retrieval_assist",
                "description": (
                    "Suggest alternative retrieval cues when a query "
                    "stalls: mines stored cues and content terms that "
                    "overlap the (synonym-expanded) query."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "schema_report",
                "description": (
                    "Group memories into topic schemas by their primary "
                    "cue: cluster size, average importance, kind mix and "
                    "samples (schema theory, Bartlett 1932)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "suppress_memories",
                "description": (
                    "Temporarily block memories from retrieval (directed "
                    "forgetting): traces stay in the store but stop "
                    "surfacing in recall until unsuppressed."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["memory_ids"],
                },
            },
            {
                "name": "unsuppress_memories",
                "description": "Restore suppressed memories to retrieval.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["memory_ids"],
                },
            },
            {
                "name": "suppressed_report",
                "description": (
                    "List currently suppressed memories with previews."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "timeline_report",
                "description": (
                    "Autobiographical timeline: episodic memories in "
                    "chronological order grouped by day, optionally within "
                    "a start/end window."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "start": {"type": "string"},
                        "end": {"type": "string"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "recognition_check",
                "description": (
                    "Classify one candidate memory against a query as "
                    "recollection (specific evidence), familiarity (vague "
                    "match) or unmatched (dual-process theory, Yonelinas "
                    "2002)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string"},
                        "memory_id": {"type": "string"},
                    },
                    "required": ["query", "memory_id"],
                },
            },
            {
                "name": "interference_report",
                "description": (
                    "Report cue-crowded clusters (too many memories on "
                    "one cue) that cause interference, with a suggestion "
                    "to add differentiating cues (Wickens 1972)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "shared_cue_min": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "life_story",
                "description": (
                    "Summarize the store as lifetime periods: group "
                    "episodic traces into time buckets with event counts, "
                    "top themes, average importance and highlights "
                    "(Conway & Pleydell-Pearce 2000)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "period_days": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "intent_conflicts",
                "description": (
                    "Detect intention clashes: two active intentions due "
                    "within a short window, or sharing the same context "
                    "cue."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "time_window_minutes": {"type": "integer"},
                    },
                },
            },
            {
                "name": "memory_health",
                "description": (
                    "One overall memory-health score (0-100) with "
                    "itemized penalties: linked ratio, crowded cues, "
                    "conflicts, overdue/clashing intentions and "
                    "suppressed memories (metacognitive monitoring)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "kg_export",
                "description": (
                    "Export the memory network as a knowledge-graph edge "
                    "list (nodes + deduplicated undirected edges) for "
                    "external visualization (semantic networks, Collins & "
                    "Quillian 1969)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "learner_profile",
                "description": (
                    "Estimate learning rate from review history and return "
                    "a profile (fast/steady/struggling) plus a suggested "
                    "review-interval scale (adaptive spacing, Mozer et al. "
                    "2009)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "context_pack",
                "description": (
                    "Pack the best matching memories for several queries "
                    "into one bounded context: deduplicated, score-ranked, "
                    "character-budgeted (cognitive load, Sweller 1988)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "top_k": {"type": "integer"},
                        "max_chars": {"type": "integer"},
                    },
                    "required": ["queries"],
                },
            },
            {
                "name": "practice_due",
                "description": (
                    "Active retrieval practice: list due memories as cues "
                    "only (no answer), for testing-effect self-quizzing."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                        "desirable_difficulty": {"type": "boolean"},
                        "min_gap_hours": {"type": "number"},
                        "adaptive_gap": {"type": "boolean"},
                        "interleave": {"type": "boolean"},
                        "vary_cues": {"type": "boolean"},
                        "arousal_priority": {"type": "boolean"},
                        "fresh_priority": {"type": "boolean"},
                        "kind": {"type": "string",
                                 "enum": ["semantic", "episodic"]},
                    },
                },
            },
            {
                "name": "practice_answer",
                "description": (
                    "Score a retrieval attempt, apply testing-effect "
                    "reinforcement, and return the correct content as "
                    "feedback."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "attempt": {"type": "string"},
                        "suppress_competitors": {"type": "boolean"},
                        "generation_bonus": {"type": "boolean"},
                    },
                    "required": ["memory_id", "attempt"],
                },
            },
            {
                "name": "practice_report",
                "description": (
                    "Score a whole practice round (list of id/attempt) and "
                    "return one session report with per-card feedback."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "answers": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "attempt": {"type": "string"},
                                },
                                "required": ["id"],
                            },
                        }
                    },
                    "required": ["answers"],
                },
            },
            {
                "name": "practice_plan",
                "description": (
                    "Return the next practice session as a review plan: "
                    "each card with its scheduled next review time, current "
                    "retrievability, and historical success rate."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "practice_forecast",
                "description": (
                    "Forecast which memories are due within the next N "
                    "days, with due times, so the agent can plan a week of "
                    "reviews ahead of time."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer"},
                    },
                },
            },
        ]

    def handle_line(self, line: str) -> str | None:
        """Handle one JSON-RPC message; return a response line or None."""
        line = line.strip()
        if not line:
            return None
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            return self._error(None, -32700, "Parse error")

        method = message.get("method")
        message_id = message.get("id")
        if message_id is None:
            return None  # notification

        if method == "initialize":
            return self._result(
                message_id,
                {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "mnemosis", "version": "0.2.0"},
                },
            )
        if method == "ping":
            return self._result(message_id, {})
        if method == "tools/list":
            return self._result(message_id, {"tools": self._tools})
        if method == "tools/call":
            params = message.get("params", {}) or {}
            name = params.get("name", "")
            arguments = params.get("arguments", {}) or {}
            try:
                payload = self._call_tool(name, arguments)
                return self._result(
                    message_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(
                                    payload, ensure_ascii=False, indent=2
                                ),
                            }
                        ],
                        "isError": False,
                    },
                )
            except Exception as exc:  # noqa: BLE001 - surface tool errors
                return self._result(
                    message_id,
                    {
                        "content": [{"type": "text", "text": f"error: {exc}"}],
                        "isError": True,
                    },
                )
        return self._error(message_id, -32601, f"Method not found: {method}")

    def _call_tool(self, name: str, args: dict[str, Any]) -> Any:
        if name == "remember":
            item = self.engine.remember(
                args["content"],
                kind=_kind(args.get("kind")) or MemoryKind.EPISODIC,
                source=SourceRecord(
                    origin=SourceType(args.get("source", SourceType.USER.value))
                ),
                cues=args.get("cues"),
                context=args.get("context"),
                affect=args.get("affect"),
                importance=args.get("importance"),
                confidence=float(args.get("confidence", 1.0)),
                evidence_count=int(args.get("evidence_count", 1)),
            )
            return {
                "id": item.id,
                "kind": item.kind.value,
                "content": item.content,
                "cues": item.cues,
                "importance": item.importance,
            }
        if name == "recall":
            embedder = (
                NGramEmbedder()
                if args.get("embedder") == "ngram"
                else None
            )
            results = self.engine.recall(
                args["query"],
                kind=_kind(args.get("kind")),
                top_k=int(args.get("top_k", 5)),
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
        if name == "search_batch":
            return self.engine.search_batch(
                args["queries"],
                kind=_kind(args.get("kind")),
                top_k=int(args.get("top_k", 3)),
            )
        if name == "sleep":
            report = self.engine.sleep()
            return {
                "summary": report.summary(),
                "promoted": len(report.promoted),
                "pruned": len(report.recycled),
                "reflected": len(report.reflected),
                "conflicts": len(report.conflicts),
            }
        if name == "check":
            check = self.engine.check(args["query"], top_k=int(args.get("top_k", 3)))
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
        if name == "update":
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
        if name == "forget":
            return {"ok": self.engine.forget(args["memory_id"])}
        if name == "restore":
            return {"ok": self.engine.restore(args["memory_id"])}
        if name == "stats":
            return self.engine.stats()
        if name == "working_set":
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
                for item in self.engine.working_set(limit=int(args.get("limit", 8)))
            ]
        if name == "review_due":
            return [
                {
                    "id": item.id,
                    "content": item.content,
                    "retrievability": round(
                        self.engine.curve.retrievability(item), 3
                    ),
                }
                for item in self.engine.review_due(
                    limit=int(args.get("limit", 10)),
                    desirable_difficulty=bool(
                        args.get("desirable_difficulty", False)
                    ),
                    difficulty_target=float(
                        args.get("difficulty_target", 0.45)
                    ),
                )
            ]
        if name == "review":
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
        if name == "plan":
            results = self.engine.plan_for_goal(
                args["goal"],
                top_k=(
                    int(args["top_k"])
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
        if name == "reason":
            results = self.engine.recall_reasoning(
                args["query"], top_k=int(args.get("top_k", 8))
            )
            return [
                {
                    "content": r.item.content,
                    "score": round(r.score, 3),
                    "reasons": r.reasons,
                }
                for r in results
            ]
        if name == "record_outcome":
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
        if name == "replan":
            results = self.engine.replan(
                args["goal"],
                args["failed_step"],
                top_k=(
                    int(args["top_k"])
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
        if name == "predict_step":
            return self.engine.predict_step(args["step"])
        if name == "sleep_replay":
            return self.engine.sleep_replay()
        if name == "search":
            results = self.engine.recall(
                args["query"],
                top_k=int(args.get("top_k", 5)),
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
        if name == "list_conflicts":
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
        if name == "memory_status":
            return self.engine.memory_status()
        if name == "review_batch":
            return self.engine.review_batch(args["answers"])
        if name == "export_memories":
            return self.engine.export_memories()
        if name == "import_memories":
            return self.engine.import_memories(args["payload"])
        if name == "practice_session":
            return self.engine.practice_session(
                args["answers"],
                limit=int(args.get("limit", 5)),
            )
        if name == "sleep_and_plan":
            return self.engine.sleep_and_plan(
                days=int(args.get("days", 7))
            )
        if name == "memory_audit":
            return self.engine.memory_audit()
        if name == "dedupe_memories":
            return self.engine.dedupe_memories()
        if name == "resolve_conflicts":
            return self.engine.resolve_conflicts()
        if name == "review_load":
            return self.engine.review_load(
                days=int(args.get("days", 7))
            )
        if name == "tag_memories":
            return self.engine.tag_memories(
                args["memory_ids"],
                args["tags"],
                action=args.get("action", "add"),
            )
        if name == "recall_log":
            return self.engine.get_recall_log(
                limit=int(args.get("limit", 50))
            )
        if name == "cleanup_preview":
            return self.engine.cleanup_preview(
                limit=int(args.get("limit", 100))
            )
        if name == "similarity_report":
            return self.engine.similarity_report(
                threshold=float(args.get("threshold", 0.6)),
                limit=int(args.get("limit", 20)),
            )
        if name == "association_report":
            return self.engine.association_report(
                limit=int(args.get("limit", 10)),
            )
        if name == "intent_remember":
            from datetime import datetime

            return self.engine.remember_intent(
                args["content"],
                datetime.fromisoformat(args["due_at"]),
                context_cue=args.get("context_cue"),
                importance=float(args.get("importance", 0.5)),
            )
        if name == "intent_due":
            return self.engine.intent_due(
                limit=int(args.get("limit", 10)),
            )
        if name == "intent_complete":
            return self.engine.complete_intent(args["intent_id"])
        if name == "intent_cancel":
            return self.engine.cancel_intent(args["intent_id"])
        if name == "intent_report":
            return self.engine.intent_report()
        if name == "retrieval_assist":
            return self.engine.retrieval_assist(
                args["query"],
                limit=int(args.get("limit", 8)),
            )
        if name == "schema_report":
            return self.engine.schema_report(
                limit=int(args.get("limit", 20)),
            )
        if name == "suppress_memories":
            return self.engine.suppress_memories(args["memory_ids"])
        if name == "unsuppress_memories":
            return self.engine.unsuppress_memories(args["memory_ids"])
        if name == "suppressed_report":
            return self.engine.suppressed_report()
        if name == "timeline_report":
            from datetime import datetime

            return self.engine.timeline_report(
                start=(
                    datetime.fromisoformat(args["start"])
                    if args.get("start")
                    else None
                ),
                end=(
                    datetime.fromisoformat(args["end"])
                    if args.get("end")
                    else None
                ),
                limit=int(args.get("limit", 200)),
            )
        if name == "recognition_check":
            return self.engine.recognition_check(
                args["query"], args["memory_id"]
            )
        if name == "interference_report":
            return self.engine.interference_report(
                shared_cue_min=int(args.get("shared_cue_min", 3)),
                limit=int(args.get("limit", 20)),
            )
        if name == "life_story":
            return self.engine.life_story(
                period_days=int(args.get("period_days", 30)),
                limit=int(args.get("limit", 20)),
            )
        if name == "intent_conflicts":
            return self.engine.intent_conflicts(
                time_window_minutes=int(
                    args.get("time_window_minutes", 60)
                ),
            )
        if name == "memory_health":
            return self.engine.memory_health()
        if name == "kg_export":
            return self.engine.kg_export()
        if name == "learner_profile":
            return self.engine.learner_profile()
        if name == "context_pack":
            return self.engine.context_pack(
                args["queries"],
                top_k=int(args.get("top_k", 3)),
                max_chars=int(args.get("max_chars", 1200)),
            )
        if name == "practice_due":
            kind_value = args.get("kind")
            from .types import MemoryKind

            return self.engine.practice_due(
                limit=int(args.get("limit", 5)),
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
        if name == "practice_answer":
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
        if name == "practice_report":
            return self.engine.practice_report(args["answers"])
        if name == "practice_plan":
            return self.engine.practice_plan(
                limit=int(args.get("limit", 5))
            )
        if name == "practice_forecast":
            return self.engine.practice_forecast(
                days=int(args.get("days", 7))
            )
        raise ValueError(f"unknown tool: {name}")

    def _result(self, message_id: Any, result: Any) -> str:
        return json.dumps(
            {"jsonrpc": "2.0", "id": message_id, "result": result},
            ensure_ascii=False,
        )

    def _error(self, message_id: Any, code: int, message: str) -> str:
        return json.dumps(
            {
                "jsonrpc": "2.0",
                "id": message_id,
                "error": {"code": code, "message": message},
            },
            ensure_ascii=False,
        )


def run_stdio(db_path: str | None = None) -> None:
    server = MCPServer(MemoryEngine(db_path))
    for line in sys.stdin:
        response = server.handle_line(line)
        if response is not None:
            sys.stdout.write(response + "\n")
            sys.stdout.flush()


__all__ = ["MCPServer", "run_stdio"]
