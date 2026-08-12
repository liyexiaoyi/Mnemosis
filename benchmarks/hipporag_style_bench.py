"""HippoRAG-style baseline (local emulation) vs Mnemosis on the same benchmark.

HippoRAG (NeurIPS 2024) retrieves by: LLM knowledge-graph construction
(entity/relation triples) + Personalized PageRank over the graph starting
from query entities. The hipporag package needs heavy deps, so we faithfully
emulate that mechanism with gemma3:12b (Ollama) for extraction and a pure
Python PPR implementation, then run it on the identical 88-question set.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from collections import defaultdict

from bench_utils import pin_local_src

pin_local_src()

from mnemosis import MemoryEngine
from mnemosis.embedding import NGramEmbedder
from mnemosis.types import MemoryKind, SourceRecord, SourceType, tokenize

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


def extract_triples(model: str, contents: list[str]) -> list[tuple[str, str, str]]:
    prompt = (
        "Extract knowledge graph triples from each memory. "
        "Use exactly one line per triple, format: SUBJECT|PREDICATE|OBJECT. "
        "Keep names, places, dates, foods and values.\n\n"
        + "\n".join(f"- {c}" for c in contents)
    )
    response = ollama_generate(model, prompt)
    triples = []
    for line in response.splitlines():
        parts = [p.strip() for p in line.split("|")]
        if len(parts) >= 3:
            triples.append((parts[0], parts[1], parts[2]))
    return triples


def extract_entities(model: str, questions: list[str]) -> list[list[str]]:
    prompt = (
        "For each question, list the entities (names, places, dates, foods, "
        "objects). Output exactly one line per question, entities separated "
        "by '|'.\n\n"
        + "\n".join(f"Q{i}: {q}" for i, q in enumerate(questions))
    )
    response = ollama_generate(model, prompt)
    result: list[list[str]] = []
    for line in response.splitlines():
        line = line.strip()
        if not line:
            continue
        if ":" in line and not line.startswith("Q"):
            line = line.split(":", 1)[1]
        result.append([e.strip() for e in line.split("|") if e.strip()])
    return result


def ppr(
    adj: dict[str, dict[str, float]],
    teleport_nodes: list[str],
    alpha: float = 0.85,
    iters: int = 30,
) -> dict[str, float]:
    nodes = list(adj.keys())
    index = {node: i for i, node in enumerate(nodes)}
    size = len(nodes)
    if size == 0:
        return {}
    out_deg = {node: sum(adj[node].values()) for node in nodes}
    teleport = [0.0] * size
    for node in teleport_nodes:
        if node in index:
            teleport[index[node]] += 1.0
    total = sum(teleport)
    if total <= 0:
        teleport = [1.0 / size] * size
    else:
        teleport = [t / total for t in teleport]
    rank = [1.0 / size] * size
    for _ in range(iters):
        new_rank = [(1 - alpha) * teleport[i] for i in range(size)]
        for node in nodes:
            i = index[node]
            degree = max(out_deg[node], 1e-9)
            for neighbor, weight in adj[node].items():
                if neighbor in index:
                    new_rank[index[neighbor]] += (
                        alpha * rank[i] * weight / degree
                    )
        rank = new_rank
    return {node: rank[index[node]] for node in nodes}


def run_hipporag_style(
    dataset: dict,
    questions: list[dict],
    llm_model: str,
    top_k: int = 5,
    batch_size: int = 6,
) -> dict:
    items = dataset["facts"] + dataset["events"]
    start = time.perf_counter()
    adj: dict[str, dict[str, float]] = defaultdict(dict)
    memory_nodes: list[str] = []
    for offset in range(0, len(items), batch_size):
        batch = items[offset : offset + batch_size]
        triples = extract_triples(llm_model, [item["content"] for item in batch])
        for subj, pred, obj in triples:
            adj[subj][obj] = adj[subj].get(obj, 0.0) + 1.0
            adj[obj][subj] = adj[obj].get(subj, 0.0) + 1.0
        for item in batch:
            node = f"mem_{len(memory_nodes)}"
            memory_nodes.append(item["content"])
            for triple in triples:
                for entity in (triple[0], triple[2]):
                    adj[node][entity] = adj[node].get(entity, 0.0) + 1.0
                    adj[entity][node] = adj[entity].get(node, 0.0) + 1.0
        print(f"  built KG for {min(offset + batch_size, len(items))}/{len(items)}", flush=True)
    ingest_seconds = time.perf_counter() - start

    stats: dict[str, dict] = defaultdict(
        lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    )
    details = []
    start = time.perf_counter()
    for offset in range(0, len(questions), 8):
        chunk = questions[offset : offset + 8]
        entity_lists = extract_entities(llm_model, [q["q"] for q in chunk])
        for question, entities in zip(chunk, entity_lists):
            kind = question["kind"]
            stats[kind]["n"] += 1
            query_terms = tokenize(question["q"])
            teleport = [
                node
                for node in adj
                if not node.startswith("mem_")
                and (
                    any(e.lower() in node.lower() for e in entities if e)
                    or any(term in node.lower() for term in query_terms)
                )
            ]
            scores = ppr(dict(adj), teleport)
            ranked = sorted(
                memory_nodes,
                key=lambda node: scores.get(node, 0.0),
                reverse=True,
            )
            contents = ranked[:top_k]
            if kind == "distractor":
                stats[kind]["pass"] += int(not contents)
                details.append({"kind": kind, "q": question["q"], "pass": not contents})
                continue
            expected = [t for t in question["answer"].lower().split() if t]
            hit1 = bool(contents) and all(
                t in contents[0].lower() for t in expected
            )
            hit5 = any(
                all(t in c.lower() for t in expected) for c in contents
            )
            stats[kind]["hit1"] += int(hit1)
            stats[kind]["hit5"] += int(hit5)
            details.append(
                {"kind": kind, "q": question["q"], "hit1": hit1, "hit5": hit5}
            )
    search_seconds = time.perf_counter() - start
    return {
        "stats": dict(stats),
        "details": details,
        "kg_nodes": len(adj),
        "ingest_seconds": round(ingest_seconds, 1),
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
        stats[kind]["hit1"] += int(bool(contents) and all(t in contents[0].lower() for t in expected))
        stats[kind]["hit5"] += int(any(all(t in c.lower() for t in expected) for c in contents))
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
    parser.add_argument("--skip-hipporag", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            f"hipporagstyle_vs_mnemosis_{time.strftime('%Y%m%d_%H%M%S')}.json",
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
    if not args.skip_hipporag:
        hipporag = run_hipporag_style(
            dataset, questions, args.llm_model, args.top_k
        )
        print_report("HippoRAG-style (KG+PPR)", hipporag)
        print(
            f"  KG nodes {hipporag['kg_nodes']}; "
            f"ingest {hipporag['ingest_seconds']}s, "
            f"search {hipporag['search_seconds']}s"
        )
        reports["hipporag_style"] = hipporag

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
