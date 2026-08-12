"""Command-line interface for Mnemosis (stdlib only)."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .embedding import Embedder, NGramEmbedder, make_embedder
from .engine import MemoryEngine
from .types import MemoryKind, SourceRecord, SourceType

_EMBEDDER_CHOICES = ["ngram", "ollama", "openai", "none"]


def _add_embedder_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--embedder",
        choices=_EMBEDDER_CHOICES,
        default=None,
        help=(
            "dense recall provider: ngram (built-in), ollama, openai "
            "(OpenAI-compatible), none (lexical only)"
        ),
    )
    parser.add_argument("--embedding-model", default=None)
    parser.add_argument("--embedding-base-url", default=None)
    parser.add_argument("--embedding-api-key", default=None)


def _cli_embedder(args) -> Embedder | None:
    provider = getattr(args, "embedder", None)
    if not provider or provider == "none":
        return None
    if provider == "ngram":
        return NGramEmbedder()
    return make_embedder(
        provider,
        model=args.embedding_model,
        base_url=args.embedding_base_url,
        api_key=args.embedding_api_key,
    )


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
    _add_embedder_args(p)

    sub.add_parser("sleep", help="run sleep consolidation")
    sub.add_parser("stats", help="show statistics")

    p = sub.add_parser("check", help="metacognitive check for a query")
    p.add_argument("query")
    p.add_argument("--top-k", type=int, default=3)
    _add_embedder_args(p)

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

    p = sub.add_parser(
        "memory-map",
        help="summarize topics and memory strength",
    )
    p.add_argument("--limit", type=int, default=200)
    p.add_argument("--topic-min", type=int, default=1)
    output_group = p.add_mutually_exclusive_group()
    output_group.add_argument(
        "--json",
        action="store_true",
        help="print the full JSON payload instead of a human table",
    )
    output_group.add_argument(
        "--out",
        default=None,
        help="write an SVG memory-map chart to this path",
    )

    p = sub.add_parser("review-due", help="list memories due for spaced review")
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("review", help="record a spaced-repetition outcome")
    p.add_argument("memory_id")
    p.add_argument(
        "--fail",
        action="store_true",
        help="mark the review as failed",
    )

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
            cues = (
                [c.strip() for c in args.cues.split(",") if c.strip()]
                if args.cues
                else None
            )
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
            embedder = _cli_embedder(args)
            for r in engine.recall(
                args.query,
                kind=MemoryKind(args.kind) if args.kind else None,
                top_k=args.top_k,
                context=args.context,
                embedder=embedder,
            ):
                print(f"{r.score:.3f} [{r.item.kind.value}] {r.item.content}")
        elif args.command == "sleep":
            print(engine.sleep().summary())
        elif args.command == "stats":
            for key, value in engine.stats().items():
                print(f"{key}: {value}")
        elif args.command == "memory-map":
            data = engine.memory_map(
                limit=args.limit, topic_min=args.topic_min
            )
            if args.json:
                print(json.dumps(data, ensure_ascii=False, indent=2))
            elif args.out:
                from .render import render_memory_map_svg

                svg = render_memory_map_svg(data, "Mnemosis 记忆地图")
                with open(args.out, "w", encoding="utf-8") as handle:
                    handle.write(svg)
                print(f"saved {args.out} ({len(data['topics'])} topics)")
            else:
                print(f"已采样 {data['sampled']} 条记忆")
                strength = data["strength"]
                print(
                    "强度分布: "
                    f"弱 {strength['weak']} / "
                    f"中 {strength['ok']} / "
                    f"强 {strength['strong']}"
                )
                for topic in data["topics"][:10]:
                    print(
                        f"{topic['topic']}: {topic['count']}条, "
                        f"可提取度 {topic['avg_retrievability']:.2f}"
                    )
        elif args.command == "check":
            embedder = _cli_embedder(args)
            check = engine.check(args.query, top_k=args.top_k, embedder=embedder)
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
        elif args.command == "review-due":
            for item in engine.review_due(limit=args.limit):
                print(
                    f"{item.id}  "
                    f"retrievability={engine.curve.retrievability(item):.2f}  "
                    f"{item.content}"
                )
        elif args.command == "review":
            item = engine.review(args.memory_id, success=not args.fail)
            if item is None:
                print("memory not found")
            else:
                print(
                    f"reviewed: streak={item.review_streak} "
                    f"successes={item.retrieval_successes} "
                    f"failures={item.retrieval_failures}"
                )
    finally:
        engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
