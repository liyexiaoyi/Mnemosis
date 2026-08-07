"""Real benchmark: official mem0 package (mem0ai) on the same 88 questions.

Runs the actual PyPI package (mem0ai 2.0.17) with local Ollama embeddings
(nomic-embed-text) and Chroma vector store. `infer=False` is used so the
benchmark measures the memory store/retrieval pipeline, not the LLM
fact-extraction step (which needs a cloud LLM to be representative).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

os.environ["MEM0_TELEMETRY"] = "False"  # offline benchmark: no PostHog calls

_BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.normpath(os.path.join(_BENCH_DIR, "..", "src"))
sys.path.insert(0, _BENCH_DIR)
sys.path.insert(0, _SRC_DIR)

from locomo_bench import generate_dataset  # noqa: E402


def _expected(question: dict) -> list[str]:
    return [t for t in question["answer"].lower().split() if t]


def _hit(content: str, expected: list[str]) -> bool:
    lowered = content.lower()
    return all(token in lowered for token in expected)


def run(seed: int = 42, sessions: int = 24, top_k: int = 5) -> dict:
    from mem0 import Memory

    dataset = generate_dataset(seed=seed, sessions=sessions, events_per_session=5)
    cfg = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "qwen2.5:3b",
                "ollama_base_url": "http://127.0.0.1:11434",
                "temperature": 0,
                "max_tokens": 500,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text",
                "ollama_base_url": "http://127.0.0.1:11434",
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": f"mem0_bench_{seed}_{sessions}",
                "path": os.path.join(
                    os.path.dirname(__file__), "..", "..", "work", "mem0db"
                ),
            },
        },
    }
    mem = Memory.from_config(cfg)
    t0 = time.perf_counter()
    for memory in dataset["facts"] + dataset["events"]:
        mem.add(memory["content"], user_id="u1", infer=False)
    ingest_seconds = time.perf_counter() - t0

    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    t0 = time.perf_counter()
    for question in dataset["questions"]:
        kind = question["kind"]
        stats[kind]["n"] += 1
        if kind == "distractor":
            resp = mem.search(question["q"], filters={"user_id": "u1"}, limit=top_k)
            relevant = [
                r for r in resp.get("results", []) if r.get("score", 0) > 0.2
            ]
            stats[kind]["pass"] += int(len(relevant) == 0)
            continue
        resp = mem.search(question["q"], filters={"user_id": "u1"}, limit=top_k)
        contents = [r.get("memory", "") for r in resp.get("results", [])]
        expected = _expected(question)
        stats[kind]["hit1"] += int(bool(contents) and _hit(contents[0], expected))
        stats[kind]["hit5"] += int(any(_hit(c, expected) for c in contents))
    search_seconds = time.perf_counter() - t0

    totals = {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    for values in stats.values():
        for key in totals:
            totals[key] += values[key]
    report = {
        "system": "mem0 官方包 (mem0ai 2.0.17)",
        "n_questions": totals["n"],
        "total_hit1": round(totals["hit1"] / totals["n"], 3),
        "total_hit5": round(totals["hit5"] / totals["n"], 3),
        "fact@5": round(stats["fact"]["hit5"] / stats["fact"]["n"], 3),
        "event@5": round(stats["event"]["hit5"] / stats["event"]["n"], 3),
        "temporal@5": round(
            stats["temporal"]["hit5"] / stats["temporal"]["n"], 3
        ),
        "distractor_pass": totals["pass"],
        "ingest_seconds": round(ingest_seconds, 1),
        "search_seconds": round(search_seconds, 1),
        "detail": {k: dict(v) for k, v in stats.items()},
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sessions", type=int, default=24)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            "official_mem0.json",
        ),
    )
    args = parser.parse_args()
    report = run(seed=args.seed, sessions=args.sessions)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(f"\nsaved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
