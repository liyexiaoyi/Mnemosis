"""Unified real comparison: every system scored identically.

All systems ingest the same dataset and are scored by whether the expected
answer substring appears in the top-1 / top-5 retrieved memories (same rule
as the Mem0-style and HippoRAG-style runs). Loads those saved runs for the
LLM-based pipelines and runs the local ones here.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType

try:
    from bm25_baseline import Bm25Index
    from embedding_baseline import EmbeddingBaseline
    from locomo_bench import generate_dataset
except ImportError:
    from benchmarks.bm25_baseline import Bm25Index
    from benchmarks.embedding_baseline import EmbeddingBaseline
    from benchmarks.locomo_bench import generate_dataset


def _expected(question: dict) -> list[str]:
    return [t for t in question["answer"].lower().split() if t]


def _hit(content: str, expected: list[str]) -> bool:
    lowered = content.lower()
    return all(token in lowered for token in expected)


def _summary(stats: dict) -> dict:
    totals = {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    for values in stats.values():
        for key in totals:
            totals[key] += values[key]
    return totals


def score_ranked(questions, results_provider) -> dict:
    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    for question in questions:
        kind = question["kind"]
        stats[kind]["n"] += 1
        contents, _top_score = results_provider(question)
        expected = _expected(question)
        if kind == "distractor":
            stats[kind]["pass"] += int(not contents)
            continue
        stats[kind]["hit1"] += int(bool(contents) and _hit(contents[0], expected))
        stats[kind]["hit5"] += int(any(_hit(c, expected) for c in contents))
    return dict(stats)


def run_mnemosis(dataset, questions, embedder, top_k=5) -> dict:
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
        expected = _expected(question)
        if kind == "distractor":
            stats[kind]["pass"] += int(bool(engine.check(question["q"]).gaps))
            continue
        contents = [r.item.content for r in engine.recall(question["q"], top_k=top_k)]
        stats[kind]["hit1"] += int(bool(contents) and _hit(contents[0], expected))
        stats[kind]["hit5"] += int(any(_hit(c, expected) for c in contents))
    engine.close()
    return dict(stats)


def run_bm25(dataset, questions, top_k=5) -> dict:
    index = Bm25Index(dataset["facts"] + dataset["events"])
    return score_ranked(
        questions,
        lambda q: (
            [c for c, _ in index.search(q["q"], top_k)],
            index.search(q["q"], top_k)[0][1] if index.search(q["q"], top_k) else 0.0,
        ),
    )


def run_embedding_knn(dataset, questions, top_k=5) -> dict:
    index = EmbeddingBaseline(dataset["facts"] + dataset["events"])
    return score_ranked(
        questions,
        lambda q: (
            [c for c, _ in index.search(q["q"], top_k)],
            index.search(q["q"], top_k)[0][1] if index.search(q["q"], top_k) else 0.0,
        ),
    )


def load_llm_pipeline(path: str, key: str, questions) -> dict:
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    details = data[key]["details"]
    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    for question, detail in zip(questions, details):
        kind = question["kind"]
        stats[kind]["n"] += 1
        if kind == "distractor":
            stats[kind]["pass"] += int(detail.get("pass", False))
        else:
            stats[kind]["hit1"] += int(detail.get("hit1", False))
            stats[kind]["hit5"] += int(detail.get("hit5", False))
    return dict(stats)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--mem0-json", default="benchmarks/results/mem0style_vs_mnemosis.json")
    parser.add_argument("--hipporag-json", default="benchmarks/results/hipporagstyle_vs_mnemosis2.json")
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "unified_compare.json"
        ),
    )
    args = parser.parse_args()

    dataset = generate_dataset(args.seed)
    questions = dataset["questions"]
    reports = {}
    reports["mnemosis_keyword"] = run_mnemosis(dataset, questions, None)
    reports["mnemosis_ngram"] = run_mnemosis(dataset, questions, NGramEmbedder())
    reports["bm25"] = run_bm25(dataset, questions)
    reports["embedding_knn"] = run_embedding_knn(dataset, questions)
    reports["mem0_style"] = load_llm_pipeline(
        args.mem0_json, "mem0_style", questions
    )
    reports["hipporag_style"] = load_llm_pipeline(
        args.hipporag_json, "hipporag_style", questions
    )

    print(
        f"{'system':20s} {'fact@5':>7s} {'event@5':>8s} {'temp@5':>7s} "
        f"{'distract':>9s} {'total@5':>8s}"
    )
    order = [
        ("bm25", "BM25"),
        ("embedding_knn", "嵌入 kNN"),
        ("mem0_style", "Mem0-style"),
        ("hipporag_style", "HippoRAG-style"),
        ("mnemosis_keyword", "Mnemosis 词法"),
        ("mnemosis_ngram", "Mnemosis ngram"),
    ]
    table = {}
    for key, label in order:
        stats = reports[key]
        totals = _summary(stats)
        f5 = stats["fact"]["hit5"] / max(1, stats["fact"]["n"])
        e5 = stats["event"]["hit5"] / max(1, stats["event"]["n"])
        t5 = stats["temporal"]["hit5"] / max(1, stats["temporal"]["n"])
        print(
            f"{label:20s} {f5:>7.3f} {e5:>8.3f} {t5:>7.3f} "
            f"{totals['pass']:>4d}/16 {totals['hit5'] / max(1, totals['n']):>8.3f}"
        )
        table[label] = {
            "fact@5": round(f5, 3),
            "event@5": round(e5, 3),
            "temporal@5": round(t5, 3),
            "distractor_pass": totals["pass"],
            "total@5": round(totals["hit5"] / max(1, totals["n"]), 3),
        }

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump({"table": table, "raw": reports}, handle, ensure_ascii=False, indent=2)
    print(f"\nresults saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
