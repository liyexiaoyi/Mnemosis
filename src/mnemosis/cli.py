"""Command-line interface for Mnemosis (stdlib only)."""

from __future__ import annotations

import argparse
from typing import Sequence

from .engine import MemoryEngine
from .types import MemoryKind, SourceRecord, SourceType


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mnemosis",
        description="Human-inspired memory layer for AI agents",
    )
    parser.add_argument(
        "--db",
        default=None,
        help=(
            "SQLite database path; without it each invocation uses a fresh "
            "in-memory store, so pass --db to persist across commands"
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("remember", help="store a memory")
    p.add_argument("content")
    p.add_argument("--kind", choices=["episodic", "semantic"], default="episodic")
    p.add_argument("--cues", default=None, help="comma-separated cues")
    p.add_argument("--context")
    p.add_argument(
        "--affect", choices=["positive", "negative", "arousing", "mixed", "neutral"]
    )
    p.add_argument("--importance", type=float)
    p.add_argument("--confidence", type=float, default=1.0)
    p.add_argument(
        "--source",
        choices=[t.value for t in SourceType],
        default=SourceType.USER.value,
    )

    p = sub.add_parser("recall", help="recall memories")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=5)
    p.add_argument("--kind", choices=["episodic", "semantic"])
    p.add_argument("--context")

    sub.add_parser("sleep", help="run sleep consolidation")
    sub.add_parser("stats", help="show statistics")

    p = sub.add_parser("check", help="metacognitive check for a query")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=3)

    p = sub.add_parser("update", help="revise a memory")
    p.add_argument("memory_id")
    p.add_argument("--content")
    p.add_argument("--importance", type=float)
    p.add_argument("--confidence", type=float)

    p = sub.add_parser("forget", help="move a memory to the recycle bin")
    p.add_argument("memory_id")

    p = sub.add_parser("restore", help="restore a memory from the recycle bin")
    p.add_argument("memory_id")

    sub.add_parser("purge", help="purge the recycle bin")

    p = sub.add_parser("working-set", help="recently used memories")
    p.add_argument("--limit", type=int, default=8)

    p = sub.add_parser("mcp", help="run the MCP stdio server")
    p.add_argument("--db")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "mcp":
        from .mcp_server import run_stdio

        run_stdio(args.db)
        return 0

    engine = MemoryEngine(args.db)
    try:
        if args.command == "remember":
            cues = [c.strip() for c in args.cues.split(",")] if args.cues else None
            item = engine.remember(
                args.content,
                kind=MemoryKind(args.kind),
                source=SourceRecord(origin=SourceType(args.source)),
                cues=cues,
                context=args.context,
                affect=args.affect,
                importance=args.importance,
                confidence=args.confidence,
            )
            print(f"saved {item.id} [{item.kind.value}] {item.content}")
        elif args.command == "recall":
            for r in engine.recall(
                args.query,
                kind=MemoryKind(args.kind) if args.kind else None,
                top_k=args.top_k,
                context=args.context,
            ):
                print(f"{r.score:.3f} [{r.item.kind.value}] {r.item.content}")
        elif args.command == "sleep":
            print(engine.sleep().summary())
        elif args.command == "stats":
            for key, value in engine.stats().items():
                print(f"{key}: {value}")
        elif args.command == "check":
            check = engine.check(args.query, top_k=args.top_k)
            print(f"gaps: {check.gaps or 'none'}")
            print(f"contradictions: {len(check.contradictions)}")
            print(f"blocked: {[b.content for b in check.blocked] or 'none'}")
            for item, label, value in check.items:
                print(f"{label.value} ({value}) {item.content}")
        elif args.command == "update":
            item = engine.update(
                args.memory_id,
                content=args.content,
                importance=args.importance,
                confidence=args.confidence,
            )
            if item is None:
                print("not found")
            else:
                print(
                    f"updated {item.id} (revisions={item.revision_count}) "
                    f"{item.content}"
                )
        elif args.command == "forget":
            print("forgot" if engine.forget(args.memory_id) else "not found")
        elif args.command == "restore":
            print("restored" if engine.restore(args.memory_id) else "not found")
        elif args.command == "purge":
            print(f"purged {engine.purge()} memories")
        elif args.command == "working-set":
            for item in engine.working_set(limit=args.limit):
                print(item.content)
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
