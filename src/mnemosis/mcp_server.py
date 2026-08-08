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
                "description": "List memories due for spaced review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {"limit": {"type": "integer"}},
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
                    limit=int(args.get("limit", 10))
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
                args["goal"], top_k=int(args.get("top_k", 8))
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
