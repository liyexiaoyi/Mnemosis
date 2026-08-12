"""Mem0-style pipeline (local emulation) vs Mnemosis on the same benchmark.

Mem0's core mechanism: LLM fact-extraction + embedding retrieval. The mem0
package itself could not be installed here (pip stalls on this machine), so
we faithfully emulate that pipeline with the same local ingredients:
gemma3:12b (Ollama) for extraction and nomic-embed-text for embeddings.

Both pipelines ingest the identical LoCoMo-style dataset and are scored the
same way (expected answer appears in top-1 / top-5 retrieved memories).
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
import urllib.request
from collections import defaultdict

from bench_utils import pin_local_src

pin_local_src()

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType

try:
    from locomo_bench import generate_dataset
except ImportError:
    from benchmarks.locomo_bench import generate_dataset


OLLAMA_URL = "http://127.0.0.1:11434"


def ollama_generate(model: str, prompt: str, timeout: int = 180) -> str:
    payload = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("response", "").strip()


def ollama_embed(model: str, text: str, timeout: int = 120) -> list[float]:
    payload = json.dumps({"model": model, "prompt": text}).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL + "/api/embeddings",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data["embedding"]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    return dot / (norm_a * norm_b) if norm_a and norm_b else 0.0


def extract_facts_batch(model: str, contents: list[str]) -> list[str]:
    prompt = (
        "Extract every distinct fact from the memories below. "
        "Keep names, dates and exact values. Output only the facts, "
        "one per line, no numbering.\n\n"
        + "\n".join(f"- {c}" for c in contents)
    )
    response = ollama_generate(model, prompt)
    facts = [
        line.strip("- ").strip()
        for line in response.splitlines()
        if line.strip()
    ]
    return facts


def _hit(content: str, expected_tokens: list[str]) -> bool:
    lowered = content.lower()
    return all(token in lowered for token in expected_tokens)


def run_mem0_style(
    dataset: dict,
    questions: list[dict],
    llm_model: str,
    embed_model: str,
    top_k: int = 5,
    batch_size: int = 6,
) -> dict:
    items = dataset["facts"] + dataset["events"]
    start = time.perf_counter()
    stored: list[str] = []
    for offset in range(0, len(items), batch_size):
        batch = [item["content"] for item in items[offset : offset + batch_size]]
        stored.extend(extract_facts_batch(llm_model, batch))
        print(f"  extracted {len(stored)}/{len(items)} facts", flush=True)
    ingest_seconds = time.perf_counter() - start

    start = time.perf_counter()
    vectors = [ollama_embed(embed_model, text) for text in stored]
    embed_seconds = time.perf_counter() - start

    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    details = []
    start = time.perf_counter()
    for question in questions:
        kind = question["kind"]
        stats[kind]["n"] += 1
        query_vector = ollama_embed(embed_model, question["q"])
        scored = sorted(
            range(len(stored)),
            key=lambda i: cosine(query_vector, vectors[i]),
            reverse=True,
        )
        contents = [stored[i] for i in scored[:top_k]]
        top_similarity = cosine(query_vector, vectors[scored[0]]) if scored else 0.0
        if kind == "distractor":
            passed = top_similarity < 0.35
            stats[kind]["pass"] += int(passed)
            details.append({"kind": kind, "q": question["q"], "pass": passed})
            continue
        expected = [t for t in question["answer"].lower().split() if t]
        hit1 = bool(contents) and _hit(contents[0], expected)
        hit5 = any(_hit(c, expected) for c in contents)
        stats[kind]["hit1"] += int(hit1)
        stats[kind]["hit5"] += int(hit5)
        details.append(
            {
                "kind": kind,
                "q": question["q"],
                "hit1": hit1,
                "hit5": hit5,
                "top": contents,
            }
        )
    search_seconds = time.perf_counter() - start
    return {
        "stats": dict(stats),
        "details": details,
        "n_facts_extracted": len(stored),
        "ingest_seconds": round(ingest_seconds, 1),
        "embed_seconds": round(embed_seconds, 1),
        "search_seconds": round(search_seconds, 1),
    }


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
            stats[kind]["pass"] += int(bool(engine.check(question["q"]).gaps))
            continue
        results = engine.recall(question["q"], top_k=top_k)
        contents = [r.item.content for r in results]
        expected = [t for t in question["answer"].lower().split() if t]
        stats[kind]["hit1"] += int(bool(contents) and _hit(contents[0], expected))
        stats[kind]["hit5"] += int(any(_hit(c, expected) for c in contents))
    engine.close()
    return {"stats": dict(stats), "details": []}


def print_report(label: str, report: dict) -> None:
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
    parser.add_argument("--llm-model", default="gemma3:12b")
    parser.add_argument("--embed-model", default="nomic-embed-text")
    parser.add_argument("--skip-mem0-style", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            f"mem0style_vs_mnemosis_{time.strftime('%Y%m%d_%H%M%S')}.json",
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

    if not args.skip_mem0_style:
        mem0style = run_mem0_style(
            dataset, questions, args.llm_model, args.embed_model, args.top_k
        )
        print_report("Mem0-style (LLM提取+向量检索)", mem0style)
        print(
            f"  extracted {mem0style['n_facts_extracted']} facts; "
            f"ingest {mem0style['ingest_seconds']}s, "
            f"embed {mem0style['embed_seconds']}s, "
            f"search {mem0style['search_seconds']}s"
        )
        reports["mem0_style"] = mem0style

    for label, embedder in (
        ("mnemosis_keyword", None),
        ("mnemosis_ngram", NGramEmbedder()),
    ):
        report = run_mnemosis(dataset, questions, embedder, args.top_k)
        print_report("Mnemosis " + label.replace("mnemosis_", ""), report)
        reports[label] = report

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(reports, handle, ensure_ascii=False, indent=2)
    print(f"\nresults saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

