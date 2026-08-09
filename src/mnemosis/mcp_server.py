"""Minimal stdio MCP server for Mnemosis.

Implemented on `stdlib` only (JSON-RPC 2.0 over newline-delimited stdio), so
it follows the project's zero-dependency rule and can be wired into Claude
Code, Codex, or any MCP client:

    mnemosis mcp --db memory.db
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from typing import Any, Sequence

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
                "name": "encoding_quality",
                "description": (
                    "Score how well one memory was encoded (0-100): cues, "
                    "context, affect, importance, strength, length - with "
                    "improvement suggestions (elaborative encoding, Craik "
                    "& Tulving 1975)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                    },
                    "required": ["memory_id"],
                },
            },
            {
                "name": "explain_memory",
                "description": (
                    "Explain one memory's full state: content, cues, "
                    "retrievability, importance, strength, confidence, "
                    "evidence, links, suppression, access and review "
                    "state."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                    },
                    "required": ["memory_id"],
                },
            },
            {
                "name": "compare_memories",
                "description": (
                    "Compare two memories: token overlap, shared cues and "
                    "a verdict (duplicate / conflict / distinct) for "
                    "source monitoring and schema integration (Johnson et "
                    "al. 1993)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "id_a": {"type": "string"},
                        "id_b": {"type": "string"},
                    },
                    "required": ["id_a", "id_b"],
                },
            },
            {
                "name": "action_queue",
                "description": (
                    "Order active intentions as an action queue: overdue "
                    "first, then upcoming by deadline, with clashing "
                    "intentions flagged (goal-directed priority, ACT-R; "
                    "Anderson 1983)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "summarize_cluster",
                "description": (
                    "Summarize a cluster of related memories as one gist: "
                    "shared cues, frequent terms, evidence and previews "
                    "(fuzzy-trace theory, Brainerd & Reyna 1990)."
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
                "name": "multi_hop_report",
                "description": (
                    "Walk the association network hop by hop from a start "
                    "memory: which memories are 1 hop, 2 hops etc. away "
                    "(spreading activation, Collins & Loftus 1975)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "start_id": {"type": "string"},
                        "depth": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["start_id"],
                },
            },
            {
                "name": "cramming_plan",
                "description": (
                    "Plan a last-minute review schedule before a deadline: "
                    "short spaced sessions covering the most at-risk "
                    "important memories first (spacing beats massing; "
                    "Cepeda et al. 2006)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "target_at": {"type": "string"},
                        "hours_available": {"type": "number"},
                        "session_minutes": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                    "required": ["target_at"],
                },
            },
            {
                "name": "session_summary",
                "description": (
                    "Summarize one work session's memories: semantic "
                    "facts, episodic events, plus conflict and duplicate "
                    "pairs for post-session consolidation."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "compare_limit": {"type": "integer"},
                    },
                    "required": ["memory_ids"],
                },
            },
            {
                "name": "topic_drift_report",
                "description": (
                    "Compare topic distribution between the two most "
                    "recent periods: which themes grew, shrank, appeared "
                    "or disappeared (schema reconstruction, Bartlett "
                    "1932)."
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
                "name": "forgetting_export",
                "description": (
                    "Export a memory's predicted forgetting curve: "
                    "retrievability at regular intervals (forgetting "
                    "curve, Ebbinghaus 1885)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "days": {"type": "integer"},
                        "step_days": {"type": "integer"},
                    },
                    "required": ["memory_id"],
                },
            },
            {
                "name": "coverage_report",
                "description": (
                    "Report review coverage per topic schema: memory "
                    "count, reviewed count, coverage ratio, average "
                    "retrievability/importance and status."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "source_calibration",
                "description": (
                    "Score the trustworthiness of each memory source "
                    "from average confidence, evidence, importance and "
                    "source trust (source monitoring, Johnson et al. "
                    "1993)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "forgetting_risk",
                "description": (
                    "Rank memories by forgetting risk (importance x "
                    "forgetting): the riskiest ones should be reviewed "
                    "first."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "bridge_suggestions",
                "description": (
                    "Suggest missing links between memories that share "
                    "cues (network gap in spreading activation; Collins & "
                    "Loftus 1975)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "plan_quality",
                "description": (
                    "Score a Chinese agent plan's quality: step count, "
                    "explicit verbs, dependency ordering, duplicates and "
                    "alignment with project memories (cognitive control, "
                    "Miller & Cohen 2001; means-ends analysis, Newell & "
                    "Simon 1972)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "context_memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["plan"],
                },
            },
            {
                "name": "project_brief",
                "description": (
                    "Assemble a project brief from related memories and "
                    "intentions: background, known requirements, known "
                    "risks and pending actions (schema activation, "
                    "Bartlett 1932)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "limit": {"type": "integer"},
                    },
                    "required": ["title"],
                },
            },
            {
                "name": "numeric_reasoning",
                "description": (
                    "Sanity-check numbers and units in a Chinese math or "
                    "physics problem: unit mixes, division by zero, and "
                    "consistency with known facts in memory (number sense, "
                    "Dehaene 1997; mental models, Johnson-Laird 1983)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "problem": {"type": "string"},
                        "context_memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["problem"],
                },
            },
            {
                "name": "plan_support",
                "description": (
                    "Retrieve supporting memories for each plan step so "
                    "the agent executes with context (working memory pulls "
                    "from long-term memory; Baddeley & Hitch 1974)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "top_k": {"type": "integer"},
                    },
                    "required": ["plan"],
                },
            },
            {
                "name": "dependency_map",
                "description": (
                    "Build a plan's dependency graph and critical path "
                    "(hierarchical planning, Miller & Cohen 2001; "
                    "critical-path method): levels, predecessors, "
                    "parallel groups and the gating chain."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                    },
                    "required": ["plan"],
                },
            },
            {
                "name": "project_risk",
                "description": (
                    "Score project risk from memories and intention "
                    "state: known problem traces, conflicts, overdue "
                    "intentions and clashing schedules (memory-driven "
                    "risk management)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "compare_limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "plan_tracker",
                "description": (
                    "Track execution status of each plan step "
                    "(pending / in_progress / done / blocked) with a "
                    "completion ratio (goal monitoring, Miller & Cohen "
                    "2001)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "statuses": {"type": "object"},
                    },
                    "required": ["plan"],
                },
            },
            {
                "name": "plan_rewrite",
                "description": (
                    "Rewrite a weak Chinese plan into an executable one: "
                    "normalize steps to action verbs, remove duplicates "
                    "and order along the standard build flow (executive "
                    "planning, Miller & Cohen 2001)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                    },
                    "required": ["plan"],
                },
            },
            {
                "name": "lesson_learned",
                "description": (
                    "Extract lessons learned from project memories: "
                    "successes, failures and lessons as reusable schemas "
                    "(schema reuse, Bartlett 1932)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "effort_estimate",
                "description": (
                    "Estimate per-step and total effort for a plan, "
                    "including critical-path hours and a 20% buffer for "
                    "the planning fallacy (Buehler et al. 1994)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "base_hours": {"type": "number"},
                    },
                    "required": ["plan"],
                },
            },
            {
                "name": "decision_review",
                "description": (
                    "Review a finished plan against its results: success "
                    "rate, score, verdict, patterns and distilled lessons "
                    "(post-task metacognitive monitoring, Koriat & "
                    "Goldsmith 1996)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "results": {"type": "object"},
                    },
                    "required": ["plan", "results"],
                },
            },
            {
                "name": "transfer_report",
                "description": (
                    "Map past lessons onto a new plan's steps by token "
                    "overlap, so reusable schemas transfer to the new "
                    "task (schema reuse, Bartlett 1932)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "array",
                            "items": {
                                "oneOf": [
                                    {"type": "string"},
                                    {"type": "object"},
                                ]
                            },
                        },
                        "lessons_memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": ["plan"],
                },
            },
            {
                "name": "retrieval_quality",
                "description": (
                    "Measure retrieval quality across queries: average "
                    "top score, retrievability, hit rate and weak rate "
                    "(metacognitive monitoring of retrieval, Koriat & "
                    "Goldsmith 1996)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "queries": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "top_k": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "recall_trace",
                "description": (
                    "Explain why a query recalls what it recalls: "
                    "candidates scanned, top results with scores and "
                    "reasons (metacognitive explanation)."
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
                "name": "community_report",
                "description": (
                    "Detect memory communities in the association "
                    "network (connected components): cluster sizes, "
                    "members and top cues."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "sleep_advice",
                "description": (
                    "Advise what to review before sleep for better "
                    "consolidation: weak-but-important memories, conflicts, "
                    "overdue intentions and tomorrow's unreviewed topics "
                    "(sleep consolidation, Rasch & Born 2013)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "emotion_advice",
                "description": (
                    "Profile the emotional tone of memories and advise "
                    "regulation: positive/negative/neutral/arousing "
                    "counts, negative ratio and reappraisal suggestions "
                    "(emotion regulation, Gross 2002)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                },
            },
            {
                "name": "difficulty_estimator",
                "description": (
                    "Estimate the current learning difficulty of memories "
                    "(desirable difficulty, Bjork 1994): too-easy / "
                    "sweet-spot / hard / very-hard buckets, topic summary "
                    "and next-action advice."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "memory_integration",
                "description": (
                    "Suggest how related memories can be integrated or "
                    "composed: same-topic schema candidates, nearby "
                    "episode chains and unresolved conflicts "
                    "(compositional inference; Schwartenbeck et al., 2023)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "reasoning_trace",
                "description": (
                    "Build a replay-friendly reasoning trace from stored "
                    "memories: recall evidence, extract quantities, build "
                    "per-step trace and optionally store the derived "
                    "conclusion as an inference memory (math reasoning "
                    "circuits; Menon, 2016; Watanabe et al., 2023)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "problem": {"type": "string"},
                        "topic": {"type": "string"},
                        "top_k": {"type": "integer"},
                        "store_conclusion": {"type": "boolean"},
                    },
                    "required": ["problem"],
                },
            },
            {
                "name": "goal_replay",
                "description": (
                    "Replay goal-related memories to plan the next move: "
                    "recall evidence, extract past lessons, reactivate "
                    "overdue intentions and score replay readiness "
                    "(prefrontal-hippocampal replay; Jensen et al., 2024; "
                    "Watanabe et al., 2023)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["goal"],
                },
            },
            {
                "name": "sleep_inference",
                "description": (
                    "Find same-topic memory pairs that sleep can weave "
                    "into new inferences, ranked by consolidation "
                    "readiness (NREM/REM inferential weaving; Abdou, "
                    "Nomoto et al., 2024)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "schema_fit",
                "description": (
                    "Measure how each memory fits existing schemas "
                    "(topic groups) and label it assimilate / borderline / "
                    "accommodate (schema-based consolidation; Tse et al., "
                    "2007; Bartlett, 1932)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "working_set_budget",
                "description": (
                    "Check whether the working set fits working-memory "
                    "capacity and recommend topic chunking when overloaded "
                    "(7±2 chunks, Miller 1956; 4±1 focus, Cowan 2001; "
                    "cognitive load, Sweller 1988)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                        "capacity": {"type": "integer"},
                        "optimal": {"type": "integer"},
                    },
                },
            },
            {
                "name": "test_generator",
                "description": (
                    "Generate retrieval-practice questions (cue prompts "
                    "and cloze blanks) from memories with answers hidden, "
                    "for self-testing (testing effect; Roediger & "
                    "Karpicke, 2006)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "memory_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "count": {"type": "integer"},
                    },
                },
            },
            {
                "name": "spacing_plan",
                "description": (
                    "Build a spaced review schedule: fading memories "
                    "early, strong ones later, topics interleaved "
                    "(distributed practice; Cepeda et al., 2006)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "rumination_check",
                "description": (
                    "Detect repeated retrieval of negative/arousing "
                    "memories (rumination risk) and suggest reappraisal "
                    "plus memory update instead of another replay "
                    "(Watkins, 2008; Nader et al., 2000)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "access_threshold": {"type": "integer"},
                    },
                },
            },
            {
                "name": "consolidation_forecast",
                "description": (
                    "Predict which memories gain most from overnight "
                    "consolidation (importance + emotional salience + "
                    "weakness) and list tonight's review candidates "
                    "(sleep consolidation; Rasch & Born, 2013)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "forgetting_balance",
                "description": (
                    "Detect within-topic access imbalance: repeated "
                    "retrieval of one memory may suppress its siblings "
                    "(retrieval-induced forgetting; Anderson, Bjork & "
                    "Bjork, 1994)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "imbalance_ratio": {"type": "number"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "metacog_report",
                "description": (
                    "Aggregate confidence vs retrieval accuracy per "
                    "topic and flag overconfidence / underconfidence "
                    "(metacognitive monitoring; Koriat, 1997)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "min_attempts": {"type": "integer"},
                    },
                },
            },
            {
                "name": "reconsolidation_plan",
                "description": (
                    "Produce an update plan for a memory that needs "
                    "revision: gather conflicting evidence and return "
                    "retrieve -> update -> reconsolidate steps (Nader et "
                    "al., 2000)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                    },
                    "required": ["memory_id"],
                },
            },
            {
                "name": "mastery_map",
                "description": (
                    "Estimate per-topic mastery (accuracy + "
                    "retrievability + coverage) and recommend the next "
                    "topic in the developing band (zone of proximal "
                    "development; Vygotsky, 1978)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "threshold": {"type": "number"},
                        "min_attempts": {"type": "integer"},
                    },
                },
            },
            {
                "name": "attention_filter",
                "description": (
                    "Filter memories for the current task: keep relevant "
                    "ones and flag strong-but-irrelevant distractors to "
                    "stay out of the prompt (biased competition; Desimone "
                    "& Duncan, 1995)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["task"],
                },
            },
            {
                "name": "analogy_bridge",
                "description": (
                    "Find cross-topic memory pairs with shared structure "
                    "for analogical transfer (structure-mapping; Gentner, "
                    "1983; Holyoak & Thagard, 1995)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "min_structure": {"type": "number"},
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "next_interval",
                "description": (
                    "Recommend each memory's next review interval from "
                    "retrieval history (adaptive spacing; Karpicke & "
                    "Bauernschmidt, 2011)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                    },
                },
            },
            {
                "name": "nightly_routine",
                "description": (
                    "Compose the nightly memory routine: tonight's review "
                    "candidates, sleep-inference pairs and tomorrow's "
                    "quiz (sleep consolidation; Rasch & Born, 2013; "
                    "testing effect; Roediger & Karpicke, 2006)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "review_limit": {"type": "integer"},
                        "quiz_count": {"type": "integer"},
                    },
                },
            },
            {
                "name": "cue_diversity",
                "description": (
                    "Check each memory's retrieval-cue breadth and flag "
                    "single-cue or overloaded-cue memories (encoding "
                    "specificity; Tulving & Thomson, 1973)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "weekly_review",
                "description": (
                    "Compose a weekly memory health review: coverage "
                    "blind spots, forgetting risk, calibration score and "
                    "tonight's candidates, plus a next-week plan."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "transfer_prompt",
                "description": (
                    "Generate hidden-answer application questions from "
                    "mastered topics, applying knowledge to new contexts "
                    "(far transfer; Barnett & Ceci, 2002)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                        "min_mastery": {"type": "number"},
                    },
                },
            },
            {
                "name": "curve_fit",
                "description": (
                    "Personalize each memory's forgetting forecast from "
                    "retrieval history and predict days until "
                    "retrievability crosses a threshold (individual "
                    "forgetting rates; Murre & Chessa, 2011)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "memory_id": {"type": "string"},
                        "horizon_days": {"type": "integer"},
                        "threshold": {"type": "number"},
                    },
                },
            },
            {
                "name": "affect_decay",
                "description": (
                    "Forecast emotional charge persistence: repeated "
                    "successful processing reduces charge (emotion "
                    "regulation; Gross, 2002)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                    },
                },
            },
            {
                "name": "goal_progress",
                "description": (
                    "Measure progress toward a learning goal via the "
                    "best-matching topic's mastery (self-regulated "
                    "learning goal monitoring)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                    },
                    "required": ["goal"],
                },
            },
            {
                "name": "plan_rehearsal",
                "description": (
                    "Mentally rehearse a plan before executing: predict "
                    "each step's success probability from outcome "
                    "history, flag the weakest step and offer a remembered "
                    "fallback (constructive episodic simulation; Schacter "
                    "& Addis, 2007)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "goal": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["goal"],
                },
            },
            {
                "name": "math_ladder",
                "description": (
                    "Climb the math abstraction ladder (concrete -> "
                    "symbolic -> general rule), using formulas already "
                    "stored in memory (Amalric & Dehaene, 2019; "
                    "concreteness fading)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "problem": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["problem"],
                },
            },
            {
                "name": "physics_simulate",
                "description": (
                    "Run a mental physics simulation: detect scene type, "
                    "extract quantities, recall the applicable law from "
                    "memory (or built-in rules) and play the scene "
                    "forward in ordered phases (intuitive physics engine; "
                    "Battaglia et al., 2013; Fischer et al., 2016)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "scene": {"type": "string"},
                        "top_k": {"type": "integer"},
                    },
                    "required": ["scene"],
                },
            },
            {
                "name": "analogy_prompt",
                "description": (
                    "Generate same-structure / new-surface practice "
                    "prompts from mastered memories (analogical encoding; "
                    "Gentner, Loewenstein & Thompson, 2003)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "topic": {"type": "string"},
                        "count": {"type": "integer"},
                        "min_mastery": {"type": "number"},
                    },
                },
            },
            {
                "name": "review_consistency",
                "description": (
                    "Monitor adherence to the spaced-review schedule: "
                    "flag overdue reviews, report an adherence ratio and "
                    "plain advice (Cepeda et al., 2006; self-regulated "
                    "learning monitoring)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "learning_loop",
                "description": (
                    "Build a ready-to-run learning loop: what to review "
                    "first, one self-test question for the weakest topic, "
                    "and the snapshot to take afterwards (spacing + "
                    "testing effect + knowledge tracing)."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "count": {"type": "integer"},
                    },
                },
            },
            {
                "name": "agent_learning_session",
                "description": (
                    "Run one end-to-end learning session: score practice "
                    "attempts, diff a second snapshot against the "
                    "baseline and plan the next loop (testing effect + "
                    "knowledge tracing)."
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
                        },
                        "count": {"type": "integer"},
                    },
                },
            },
            {
                "name": "concept_cover",
                "description": (
                    "Show how a multi-concept Chinese question is split "
                    "into chunks, which memories cover each chunk and "
                    "the final top-k (working-memory chunking; Miller, "
                    "1956)."
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
                "name": "temporal_anchor",
                "description": (
                    "Show which memory the time-anchor pass inserted for "
                    "a '上次/下次/最近/什么时候' style question, so agents can "
                    "verify last-vs-next retrieval picks the record with "
                    "the right date (ordinal time processing; Gauthier et "
                    "al., 2020). Read-only."
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
                "name": "retrieval_snapshot",
                "description": (
                    "Capture a compact memory-state snapshot (knowledge "
                    "tracing); pass a previous snapshot to get a progress "
                    "diff with an improving/stable/declining verdict."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "previous": {
                            "type": "object",
                            "description": (
                                "Optional previous retrieval_snapshot "
                                "report; its 'snapshot' field is diffed "
                                "against the new one."
                            ),
                        },
                    },
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
                    "serverInfo": {"name": "mnemosis", "version": "0.2.1"},
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
            except KeyError as exc:
                return self._error(
                    message_id,
                    -32602,
                    f"Invalid params: missing required field {exc.args[0]}",
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
                confidence=float(args.get("confidence") or 1.0),
                evidence_count=int(args.get("evidence_count") or 1),
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
                top_k=int(args.get("top_k") or 5),
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
                top_k=int(args.get("top_k") or 3),
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
            check = self.engine.check(args["query"], top_k=int(args.get("top_k") or 3))
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
                for item in self.engine.working_set(limit=int(args.get("limit") or 8))
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
                    limit=int(args.get("limit") or 10),
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
                    int(args.get("top_k") or 8)
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
                args["query"], top_k=int(args.get("top_k") or 8)
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
                    int(args.get("top_k") or 8)
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
                top_k=int(args.get("top_k") or 5),
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
                limit=int(args.get("limit") or 5),
            )
        if name == "sleep_and_plan":
            return self.engine.sleep_and_plan(
                days=int(args.get("days") or 7)
            )
        if name == "memory_audit":
            return self.engine.memory_audit()
        if name == "dedupe_memories":
            return self.engine.dedupe_memories()
        if name == "resolve_conflicts":
            return self.engine.resolve_conflicts()
        if name == "review_load":
            return self.engine.review_load(
                days=int(args.get("days") or 7)
            )
        if name == "tag_memories":
            return self.engine.tag_memories(
                args["memory_ids"],
                args["tags"],
                action=args.get("action", "add"),
            )
        if name == "recall_log":
            return self.engine.get_recall_log(
                limit=int(args.get("limit") or 50)
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
        if name == "encoding_quality":
            return self.engine.encoding_quality(args["memory_id"])
        if name == "explain_memory":
            return self.engine.explain_memory(args["memory_id"])
        if name == "compare_memories":
            return self.engine.compare_memories(
                args["id_a"], args["id_b"]
            )
        if name == "action_queue":
            return self.engine.action_queue(
                limit=int(args.get("limit", 20)),
            )
        if name == "summarize_cluster":
            return self.engine.summarize_cluster(args["memory_ids"])
        if name == "multi_hop_report":
            return self.engine.multi_hop_report(
                args["start_id"],
                depth=int(args.get("depth", 2)),
                limit=int(args.get("limit", 20)),
            )
        if name == "cramming_plan":

            return self.engine.cramming_plan(
                datetime.fromisoformat(args["target_at"]),
                hours_available=float(args.get("hours_available", 6.0)),
                session_minutes=int(args.get("session_minutes", 30)),
                limit=int(args.get("limit", 20)),
            )
        if name == "session_summary":
            return self.engine.session_summary(
                args["memory_ids"],
                compare_limit=int(args.get("compare_limit", 20)),
            )
        if name == "topic_drift_report":
            return self.engine.topic_drift_report(
                period_days=int(args.get("period_days", 30)),
                limit=int(args.get("limit", 20)),
            )
        if name == "forgetting_export":
            return self.engine.forgetting_export(
                args["memory_id"],
                days=int(args.get("days", 30)),
                step_days=int(args.get("step_days", 1)),
            )
        if name == "coverage_report":
            return self.engine.coverage_report(
                limit=int(args.get("limit", 20)),
            )
        if name == "source_calibration":
            return self.engine.source_calibration()
        if name == "forgetting_risk":
            return self.engine.forgetting_risk(
                limit=int(args.get("limit", 20)),
            )
        if name == "bridge_suggestions":
            return self.engine.bridge_suggestions(
                limit=int(args.get("limit", 20)),
            )
        if name == "plan_quality":
            return self.engine.plan_quality(
                args["plan"],
                context_memory_ids=args.get("context_memory_ids"),
            )
        if name == "project_brief":
            return self.engine.project_brief(
                args["title"],
                memory_ids=args.get("memory_ids"),
                limit=int(args.get("limit", 8)),
            )
        if name == "numeric_reasoning":
            return self.engine.numeric_reasoning(
                args["problem"],
                context_memory_ids=args.get("context_memory_ids"),
            )
        if name == "plan_support":
            return self.engine.plan_support(
                args["plan"],
                top_k=int(args.get("top_k", 3)),
            )
        if name == "dependency_map":
            return self.engine.dependency_map(args["plan"])
        if name == "project_risk":
            return self.engine.project_risk(
                memory_ids=args.get("memory_ids"),
                compare_limit=int(args.get("compare_limit", 20)),
            )
        if name == "plan_tracker":
            return self.engine.plan_tracker(
                args["plan"],
                statuses=args.get("statuses"),
            )
        if name == "plan_rewrite":
            return self.engine.plan_rewrite(args["plan"])
        if name == "lesson_learned":
            return self.engine.lesson_learned(
                memory_ids=args.get("memory_ids"),
                limit=int(args.get("limit", 10)),
            )
        if name == "effort_estimate":
            return self.engine.effort_estimate(
                args["plan"],
                base_hours=float(args.get("base_hours", 2.0)),
            )
        if name == "decision_review":
            return self.engine.decision_review(
                args["plan"],
                args["results"],
            )
        if name == "transfer_report":
            return self.engine.transfer_report(
                args["plan"],
                lessons_memory_ids=args.get("lessons_memory_ids"),
            )
        if name == "retrieval_quality":
            return self.engine.retrieval_quality(
                queries=args.get("queries"),
                top_k=int(args.get("top_k", 5)),
                limit=int(args.get("limit", 10)),
            )
        if name == "recall_trace":
            return self.engine.recall_trace(
                args["query"],
                top_k=int(args.get("top_k", 5)),
            )
        if name == "community_report":
            return self.engine.community_report(
                limit=int(args.get("limit", 10)),
            )
        if name == "sleep_advice":
            return self.engine.sleep_advice()
        if name == "emotion_advice":
            return self.engine.emotion_advice(
                memory_ids=args.get("memory_ids"),
            )
        if name == "difficulty_estimator":
            return self.engine.difficulty_estimator(
                limit=int(args.get("limit", 10)),
            )
        if name == "memory_integration":
            return self.engine.memory_integration(
                limit=int(args.get("limit", 10)),
            )
        if name == "reasoning_trace":
            return self.engine.reasoning_trace(
                problem=str(args.get("problem", "")),
                topic=args.get("topic"),
                top_k=int(args.get("top_k", 4)),
                store_conclusion=bool(
                    args.get("store_conclusion", True)
                ),
            )
        if name == "goal_replay":
            return self.engine.goal_replay(
                goal=str(args.get("goal", "")),
                top_k=int(args.get("top_k", 5)),
            )
        if name == "sleep_inference":
            return self.engine.sleep_inference(
                limit=int(args.get("limit", 5)),
            )
        if name == "schema_fit":
            return self.engine.schema_fit(
                limit=int(args.get("limit", 20)),
            )
        if name == "working_set_budget":
            return self.engine.working_set_budget(
                limit=int(args.get("limit", 8)),
                capacity=int(args.get("capacity", 7)),
                optimal=int(args.get("optimal", 4)),
            )
        if name == "test_generator":
            return self.engine.test_generator(
                topic=args.get("topic"),
                memory_ids=args.get("memory_ids"),
                count=int(args.get("count", 4)),
            )
        if name == "spacing_plan":
            return self.engine.spacing_plan(
                days=int(args.get("days", 7)),
                limit=int(args.get("limit", 20)),
            )
        if name == "rumination_check":
            return self.engine.rumination_check(
                access_threshold=int(args.get("access_threshold", 5)),
            )
        if name == "consolidation_forecast":
            return self.engine.consolidation_forecast(
                limit=int(args.get("limit", 5)),
            )
        if name == "forgetting_balance":
            return self.engine.forgetting_balance(
                imbalance_ratio=float(
                    args.get("imbalance_ratio", 3.0)
                ),
                limit=int(args.get("limit", 10)),
            )
        if name == "metacog_report":
            return self.engine.metacog_report(
                min_attempts=int(args.get("min_attempts", 3)),
            )
        if name == "reconsolidation_plan":
            return self.engine.reconsolidation_plan(
                memory_id=str(args.get("memory_id", "")),
            )
        if name == "mastery_map":
            return self.engine.mastery_map(
                threshold=float(args.get("threshold", 0.5)),
                min_attempts=int(args.get("min_attempts", 3)),
            )
        if name == "attention_filter":
            return self.engine.attention_filter(
                task=str(args.get("task", "")),
                top_k=int(args.get("top_k", 5)),
            )
        if name == "analogy_bridge":
            return self.engine.analogy_bridge(
                min_structure=float(args.get("min_structure", 0.3)),
                limit=int(args.get("limit", 5)),
            )
        if name == "next_interval":
            return self.engine.next_interval(
                memory_id=args.get("memory_id"),
            )
        if name == "nightly_routine":
            return self.engine.nightly_routine(
                review_limit=int(args.get("review_limit", 3)),
                quiz_count=int(args.get("quiz_count", 3)),
            )
        if name == "cue_diversity":
            return self.engine.cue_diversity(
                limit=int(args.get("limit", 20)),
            )
        if name == "weekly_review":
            return self.engine.weekly_review()
        if name == "transfer_prompt":
            return self.engine.transfer_prompt(
                count=int(args.get("count", 3)),
                min_mastery=float(args.get("min_mastery", 0.7)),
            )
        if name == "curve_fit":
            return self.engine.curve_fit(
                memory_id=args.get("memory_id"),
                horizon_days=int(args.get("horizon_days", 30)),
                threshold=float(args.get("threshold", 0.4)),
            )
        if name == "affect_decay":
            return self.engine.affect_decay(
                limit=int(args.get("limit", 20)),
            )
        if name == "goal_progress":
            return self.engine.goal_progress(
                goal=str(args.get("goal", "")),
            )
        if name == "plan_rehearsal":
            return self.engine.plan_rehearsal(
                goal=str(args.get("goal", "")),
                top_k=args.get("top_k"),
            )
        if name == "math_ladder":
            return self.engine.math_ladder(
                problem=str(args.get("problem", "")),
                top_k=int(args.get("top_k", 4)),
            )
        if name == "physics_simulate":
            return self.engine.physics_simulate(
                scene=str(args.get("scene", "")),
                top_k=int(args.get("top_k", 4)),
            )
        if name == "analogy_prompt":
            return self.engine.analogy_prompt(
                topic=args.get("topic"),
                count=int(args.get("count", 3)),
                min_mastery=float(args.get("min_mastery", 0.7)),
            )
        if name == "review_consistency":
            return self.engine.review_consistency()
        if name == "learning_loop":
            return self.engine.learning_loop(
                count=int(args.get("count", 1)),
            )
        if name == "agent_learning_session":
            return self.engine.agent_learning_session(
                answers=args.get("answers"),
                count=int(args.get("count", 1)),
            )
        if name == "concept_cover":
            return self.engine.concept_cover(
                query=str(args.get("query", "")),
                top_k=int(args.get("top_k", 4)),
            )
        if name == "temporal_anchor":
            return self.engine.temporal_anchor(
                query=str(args.get("query", "")),
                top_k=int(args.get("top_k", 4)),
            )
        if name == "retrieval_snapshot":
            return self.engine.retrieval_snapshot(
                previous=args.get("previous"),
            )
        if name == "practice_due":
            kind_value = args.get("kind")

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


def _read_message() -> str | None:
    """Read one JSON-RPC message (MCP stdio Content-Length framing)."""
    first = sys.stdin.buffer.readline()
    if not first:
        return None
    if not first.strip().lower().startswith(b"content-length"):
        return first.decode("utf-8").strip()  # legacy NDJSON line
    length = int(first.split(b":", 1)[1].strip())
    while True:
        line = sys.stdin.buffer.readline()
        if not line:
            return None
        if not line.strip():
            break
        if line.lower().startswith(b"content-length:"):
            length = int(line.split(b":", 1)[1].strip())
    if length <= 0:
        return None
    return sys.stdin.buffer.read(length).decode("utf-8")


def _write_message(text: str) -> None:
    body = text.encode("utf-8")
    sys.stdout.buffer.write(
        b"Content-Length: " + str(len(body)).encode("ascii") + b"\r\n\r\n" + body
    )
    sys.stdout.buffer.flush()


def run_stdio(db_path: str | None = None) -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    server = MCPServer(MemoryEngine(db_path))
    while True:
        message = _read_message()
        if message is None:
            break
        response = server.handle_line(message)
        if response is not None:
            _write_message(response)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="mnemosis-mcp",
        description="Mnemosis MCP server (JSON-RPC over stdio)",
    )
    parser.add_argument(
        "--db",
        default=None,
        help="SQLite path for persistent memory (default: in-memory)",
    )
    args = parser.parse_args(argv)
    run_stdio(args.db)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["MCPServer", "run_stdio", "main"]
