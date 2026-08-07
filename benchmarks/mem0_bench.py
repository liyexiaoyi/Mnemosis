"""Real head-to-head: Mem0 (local Ollama + Chroma) vs Mnemosis on the same
LoCoMo-style benchmark.

Mem0 is configured with Ollama (gemma3:12b for extraction, nomic-embed-text
for embeddings, Chroma as the local vector store). Both systems ingest the
identical dataset; retrieval is scored by whether the expected answer appears
in the retrieved memories.

Run with the Python that has mem0 installed (3.12), e.g.:
    <codex-3.12-python> benchmarks/mem0_bench.py
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import time
from collections import defaultdict

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType

try:
    from locomo_bench import generate_dataset
except ImportError:
    from benchmarks.locomo_bench import generate_dataset


def _expected_tokens(question: dict) -> list[str]:
    answer = question["answer"]
    return [part for part in answer.lower().split() if part]


def _hit(content: str, expected_tokens: list[str]) -> bool:
    lowered = content.lower()
    return all(token in lowered for token in expected_tokens)


def score_results(results: list[str], question: dict, top_k: int = 5) -> dict:
    expected = _expected_tokens(question)
    hit1 = bool(results) and _hit(results[0], expected)
    hit5 = any(_hit(r, expected) for r in results[:top_k])
    return {"hit1": hit1, "hit5": hit5}


def run_mem0(dataset: dict, questions: list[dict], top_k: int = 5) -> dict:
    from mem0 import Memory

    chroma_dir = os.path.join(
        os.path.dirname(__file__), "results", "mem0_chroma"
    )
    if os.path.exists(chroma_dir):
        shutil.rmtree(chroma_dir)

    config = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "gemma3:12b",
                "ollama_base_url": "http://localhost:11434",
                "temperature": 0,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text",
                "ollama_base_url": "http://localhost:11434",
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "mem0_bench",
                "path": chroma_dir,
            },
        },
    }
    memory = Memory.from_config(config)
    user_id = "bench"

    start = time.perf_counter()
    for item in dataset["facts"] + dataset["events"]:
        memory.add(item["content"], user_id=user_id)
    ingest_seconds = time.perf_counter() - start

    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    details = []
    start = time.perf_counter()
    for question in questions:
        kind = question["kind"]
        stats[kind]["n"] += 1
        response = memory.search(
            question["q"], user_id=user_id, limit=top_k
        )
        results = _extract_memories(response)
        if kind == "distractor":
            passed = not results
            stats[kind]["pass"] += int(passed)
            details.append({"kind": kind, "q": question["q"], "pass": passed})
            continue
        scored = score_results(results, question, top_k)
        stats[kind]["hit1"] += int(scored["hit1"])
        stats[kind]["hit5"] += int(scored["hit5"])
        details.append(
            {
                "kind": kind,
                "q": question["q"],
                "hit1": scored["hit1"],
                "hit5": scored["hit5"],
                "top": results[:top_k],
            }
        )
    search_seconds = time.perf_counter() - start
    return {
        "stats": dict(stats),
        "details": details,
        "ingest_seconds": round(ingest_seconds, 1),
        "search_seconds": round(search_seconds, 1),
    }


def _extract_memories(response) -> list[str]:
    results = response.get("results", []) if isinstance(response, dict) else response
    out = []
    for entry in results or []:
        if isinstance(entry, dict):
            text = entry.get("memory") or entry.get("text") or ""
        else:
            text = str(entry)
        if text:
            out.append(text)
    return out


def run_mnemosis(dataset: dict, questions: list[dict], embedder, top_k: int = 5) -> dict:
    engine = MemoryEngine(embedder=embedder)
    user = SourceRecord(origin=SourceType.USER)
    for item in dataset["facts"] + dataset["events"]:
        engine.remember(
            item["content"],
            kind=MemoryKind(item["kind"]),
            source=user,
            cues=item.get("cues"),
            importance=0.8 if item["kind"] == "semantic" else 0.5,
        )
    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    for question in questions:
        kind = question["kind"]
        stats[kind]["n"] += 1
        if kind == "distractor":
            gaps = engine.check(question["q"]).gaps
            stats[kind]["pass"] += int(bool(gaps))
            continue
        results = engine.recall(question["q"], top_k=top_k)
        contents = [r.item.content for r in results]
        scored = score_results(contents, question, top_k)
        stats[kind]["hit1"] += int(scored["hit1"])
        stats[kind]["hit5"] += int(scored["hit5"])
    engine.close()
    return {"stats": dict(stats), "details": []}


def print_report(label: str, report: dict, top_k: int) -> None:
    print(f"\n== {label} ==")
    print(f"{'category':12s} {'n':>4s} {'hit@1':>7s} {'hit@5':>7s} {'pass':>6s}")
    totals = {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    for kind, values in sorted(report["stats"].items()):
        n = values["n"]
        for key in totals:
            totals[key] += values[key]
        print(
            f"{kind:12s} {n:>4d} "
            f"{values['hit1'] / n if n else 0.0:>7.3f} "
            f"{values['hit5'] / n if n else 0.0:>7.3f} "
            f"{values['pass']:>6d}"
        )
    print(
        f"{'total':12s} {totals['n']:>4d} "
        f"{totals['hit1'] / totals['n']:>7.3f} "
        f"{totals['hit5'] / totals['n']:>7.3f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sessions", type=int, default=24)
    parser.add_argument("--events-per-session", type=int, default=5)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--skip-mem0", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            f"mem0_vs_mnemosis_{time.strftime('%Y%m%d_%H%M%S')}.json",
        ),
    )
    args = parser.parse_args()

    dataset = generate_dataset(args.seed, args.sessions, args.events_per_session)
    questions = dataset["questions"]
    print(
        f"dataset: {len(dataset['facts'])} facts, {len(dataset['events'])} events, "
        f"{len(questions)} questions"
    )

    reports = {}
    if not args.skip_mem0:
        mem0_report = run_mem0(dataset, questions, args.top_k)
        print_report("Mem0 (Ollama + Chroma)", mem0_report, args.top_k)
        print(
            f"  ingest {mem0_report['ingest_seconds']}s, "
            f"search {mem0_report['search_seconds']}s"
        )
        reports["mem0"] = mem0_report

    for label, embedder in (("mnemosis_keyword", None), ("mnemosis_ngram", NGramEmbedder())):
        mnemosis_report = run_mnemosis(dataset, questions, embedder, args.top_k)
        print_report(f"Mnemosis {label.replace('mnemosis_', '')}", mnemosis_report, args.top_k)
        reports[label] = mnemosis_report

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(reports, handle, ensure_ascii=False, indent=2)
    print(f"\nresults saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

