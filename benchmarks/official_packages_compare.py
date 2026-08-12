"""Unified real comparison: official installed packages vs Mnemosis.

Every system ingests the same 88-question LoCoMo dataset and is scored by the
same rule (answer tokens appear in top-5 / top-1). Systems:

- mem0ai 2.0.17 (real PyPI package, Ollama embeddings + Chroma, infer=False)
- cognitive-memory 0.5.1 (real PyPI package, hash embedder)
- Mnemosis keyword / ngram

graphiti-core / letta are installed but require external services (Neo4j,
database + agent server) that are not available on this host, so they are
reported as "installed, not runnable here" in the report.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from collections import defaultdict

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.normpath(os.path.join(_BENCH_DIR, "..", "src"))
_CM_SRC = os.path.normpath(
    os.path.join(_BENCH_DIR, "..", "..", "work", "gh_repos",
                 "cognitive-memory-main", "src")
)
sys.path.insert(0, _BENCH_DIR)
sys.path.insert(0, _SRC_DIR)
if os.path.isdir(_CM_SRC):
    sys.path.insert(0, _CM_SRC)

from locomo_bench import generate_dataset


def _expected(question: dict) -> list[str]:
    return [t for t in question["answer"].lower().split() if t]


def _hit(content: str, expected: list[str]) -> bool:
    lowered = content.lower()
    return all(token in lowered for token in expected)


def _new_stats():
    return defaultdict(lambda: {"n": 0, "hit1": 0, "hit5": 0, "pass": 0})


def _summarize(stats: dict, name: str) -> dict:
    totals = {"n": 0, "hit1": 0, "hit5": 0, "pass": 0}
    for values in stats.values():
        for key in totals:
            totals[key] += values[key]
    return {
        "name": name,
        "n": totals["n"],
        "total_hit1": round(totals["hit1"] / totals["n"], 3),
        "total_hit5": round(totals["hit5"] / totals["n"], 3),
        "fact@5": round(stats["fact"]["hit5"] / stats["fact"]["n"], 3),
        "event@5": round(stats["event"]["hit5"] / stats["event"]["n"], 3),
        "temporal@5": round(
            stats["temporal"]["hit5"] / stats["temporal"]["n"], 3
        ),
        "distractor_pass": totals["pass"],
    }


def run_mem0(dataset: dict, questions: list[dict], top_k: int = 5) -> dict:
    from mem0 import Memory

    _db_path = os.path.normpath(
        os.path.join(_BENCH_DIR, "..", "..", "work", "mem0db")
    )
    if os.path.isdir(_db_path):
        import shutil

        shutil.rmtree(_db_path)

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
                "collection_name": "mem0_official_bench",
                "path": _db_path,
            },
        },
        "history_db_path": os.path.normpath(
            os.path.join(_BENCH_DIR, "..", "..", "work", "mem0_history.db")
        ),
    }
    mem = Memory.from_config(cfg)
    t0 = time.perf_counter()
    for memory in dataset["facts"] + dataset["events"]:
        mem.add(memory["content"], user_id="u1", infer=False)
    ingest = time.perf_counter() - t0

    stats = _new_stats()
    t0 = time.perf_counter()
    for question in questions:
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
    search = time.perf_counter() - t0
    report = _summarize(stats, "mem0 官方包 (mem0ai 2.0.17)")
    report["ingest_seconds"] = round(ingest, 1)
    report["search_seconds"] = round(search, 1)
    return report


def run_cognitive_memory(dataset: dict, questions: list[dict], top_k: int = 5) -> dict:
    """Run via the system Python (where the 0.5.1 PyPI package is installed).

    The benchmark writes a request file and shells out to the system
    interpreter, because cognitive-memory 0.5.1 is not installable in this
    runtime's Python (not on PyPI for 3.12; source on GitHub is 0.1.0 with a
    different API).
    """
    import subprocess

    work = os.path.normpath(
        os.path.join(_BENCH_DIR, "..", "..", "work")
    )
    req_file = os.path.join(work, "cm_request.json")
    with open(req_file, "w", encoding="utf-8") as handle:
        json.dump({"dataset": dataset, "questions": questions, "top_k": top_k}, handle)
    out_file = os.path.join(work, "cm_result.json")
    system_python = sys.executable
    # prefer the system interpreter where 0.5.1 is installed
    candidates = [r"C:\Python314\python.exe", system_python]
    for cand in candidates:
        if os.path.exists(cand):
            system_python = cand
            break
    runner = os.path.join(_BENCH_DIR, "official_cognitive_memory_runner.py")
    subprocess.run(
        [system_python, runner, req_file, out_file],
        check=True,
        capture_output=True,
        text=True,
    )
    with open(out_file, encoding="utf-8") as handle:
        return json.load(handle)


def run_mnemosis(
    dataset: dict, questions: list[dict], embedder, label: str, top_k: int = 5
) -> dict:
    from mnemosis import MemoryEngine
    from mnemosis.types import MemoryKind, SourceRecord, SourceType

    engine = MemoryEngine(embedder=embedder)
    user = SourceRecord(origin=SourceType.USER)
    t0 = time.perf_counter()
    for memory in dataset["facts"] + dataset["events"]:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.8 if memory["kind"] == "semantic" else 0.5,
        )
    ingest = time.perf_counter() - t0

    stats = _new_stats()
    t0 = time.perf_counter()
    for question in questions:
        kind = question["kind"]
        stats[kind]["n"] += 1
        if kind == "distractor":
            gaps = engine.check(question["q"]).gaps
            stats[kind]["pass"] += int(bool(gaps))
            continue
        results = engine.recall(question["q"], top_k=top_k)
        contents = [r.item.content for r in results]
        expected = _expected(question)
        stats[kind]["hit1"] += int(bool(contents) and _hit(contents[0], expected))
        stats[kind]["hit5"] += int(any(_hit(c, expected) for c in contents))
    search = time.perf_counter() - t0
    report = _summarize(stats, label)
    report["ingest_seconds"] = round(ingest, 1)
    report["search_seconds"] = round(search, 1)
    engine.close()
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--sessions", type=int, default=24)
    parser.add_argument("--skip-mem0", action="store_true")
    parser.add_argument("--skip-cognitive", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "official_packages_compare.json"
        ),
    )
    args = parser.parse_args()

    dataset = generate_dataset(seed=args.seed, sessions=args.sessions, events_per_session=5)
    questions = dataset["questions"]
    reports = {}
    if not args.skip_mem0:
        reports["mem0_official"] = run_mem0(dataset, questions)
        print("mem0:", reports["mem0_official"])
    if not args.skip_cognitive:
        try:
            reports["cognitive_memory_official"] = run_cognitive_memory(dataset, questions)
            print("cognitive-memory:", reports["cognitive_memory_official"])
        except Exception as exc:  # noqa: BLE001 (package unavailable here)
            print("cognitive-memory skipped:", exc)

    from mnemosis.embedding import NGramEmbedder

    reports["mnemosis_keyword"] = run_mnemosis(dataset, questions, None, "Mnemosis 词法")
    print("mnemosis keyword:", reports["mnemosis_keyword"])
    reports["mnemosis_ngram"] = run_mnemosis(
        dataset, questions, NGramEmbedder(), "Mnemosis ngram"
    )
    print("mnemosis ngram:", reports["mnemosis_ngram"])

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(reports, handle, ensure_ascii=False, indent=2)
    print(f"\nsaved to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
