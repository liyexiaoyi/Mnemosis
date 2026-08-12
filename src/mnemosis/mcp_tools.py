"""MCP tool schemas (data only): manifests consumed by the MCP server."""

from __future__ import annotations

EXPERIMENTAL_TOOLS = frozenset(
    {
        "emotion_advice", "rumination_check", "sleep_advice",
        "nightly_routine", "weekly_review", "cramming_plan",
        "transfer_prompt", "analogy_prompt", "mastery_map",
        "attention_filter", "test_generator", "community_report",
        "learner_profile", "encoding_quality", "source_calibration",
        "cue_diversity", "goal_progress", "recognition_check",
        "affect_decay", "retrieval_snapshot", "retrieval_assist",
        "memory_integration", "difficulty_estimator",
        "reconsolidation_plan", "consolidation_forecast",
        "forgetting_balance", "metacog_report", "sleep_inference",
        "schema_fit", "transfer_report", "bridge_suggestions",
        "forgetting_export",
    }
)

CORE_TOOLS = frozenset(
    {
        "remember", "remember_turn", "recall", "search_batch",
        "check", "update", "forget", "restore", "stats",
        "working_set", "review_due", "review", "memory_map",
        "export_memories", "import_memories", "tag_memories",
    }
)


TOOL_DEFINITIONS: list[dict] = [
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
                "name": "remember_turn",
                "description": (
                    "Save one conversation turn in a single call: splits "
                    "the text into sentences and stores each with automatic "
                    "cues. Call this after every user/assistant exchange to "
                    "keep memory automatic."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "text": {"type": "string"},
                        "max_segments": {"type": "integer"},
                    },
                    "required": ["text"],
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
                "name": "calibrate_decay",
                "description": (
                    "Calibrate the forgetting rate from real retrieval "
                    "history (median survival span -> decay rate)."
                ),
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "rebuild_vectors",
                "description": (
                    "Re-embed active memories missing from the vector index "
                    "(repairs a failed batch embedding)."
                ),
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
                "name": "conflict_advice",
                "description": (
                    "For each memory conflict, score both sides (evidence, "
                    "confidence, recency, source trust) and recommend which "
                    "to keep or ask the user to clarify."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
                },
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
                "name": "memory_map",
                "description": (
                    "Summarize what the memory holds: topics with counts "
                    "and average retrievability, plus a weak/ok/strong "
                    "strength histogram. Powers the human-readable memory "
                    "map chart."
                ),
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "limit": {"type": "integer"},
                        "topic_min": {"type": "integer"},
                    },
                },
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
