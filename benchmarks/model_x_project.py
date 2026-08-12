"""Model x memory-project matrix on the same 12 LoCoMo questions.

Every model (Ollama Qwen models; Codex-as-model) answers the same 12
questions grounded in retrieval context from one of three *real* memory
systems:

  - Mnemosis (this repo)
  - mem0ai 2.0.17 (real PyPI package, Ollama embeddings + Chroma)
  - cognitive-memory 0.5.1 (real PyPI package, hash embedder, via system
    Python subprocess)

Scoring uses the same `score_answer` token rule as the LLM benchmark, so a
model either emits the expected answer token(s) or it does not.

Usage:
    python benchmarks/model_x_project.py --models qwen3-vl:8b qwen2.5-vl
    python benchmarks/model_x_project.py --score-codex
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from locomo_bench import generate_dataset

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

try:
    from compare_with_models import score_answer
except ImportError:  # package mode
    from benchmarks.compare_with_models import score_answer


def _generate(
    model: str,
    prompt: str,
    url: str = "http://127.0.0.1:11434",
    timeout: int = 180,
    max_tokens: int = 800,
) -> str:
    """Ollama generate with a hard output cap.

    qwen3-vl is a thinking model: it emits a long reasoning preamble before
    the short answer, so the cap must be large enough to fit reasoning +
    answer (a 90-token cap truncates mid-thought and yields an empty reply).
    """
    import json as _json
    import urllib.request

    payload = _json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": max_tokens},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = _json.loads(response.read().decode("utf-8"))
    return data.get("response", "").strip()


def select_questions(dataset: dict, limit: int = 12) -> list[dict]:
    chosen: list[dict] = []
    for kind in ("fact", "event", "temporal", "distractor"):
        pool = [q for q in dataset["questions"] if q["kind"] == kind]
        chosen.extend(pool[: max(1, limit // 4)])
    return chosen[:limit]


def _mnemosis_contexts(dataset: dict, questions: list[dict], top_k: int) -> dict:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for memory in dataset["facts"] + dataset["events"]:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.8 if memory["kind"] == "semantic" else 0.5,
        )
    contexts = {}
    for question in questions:
        k = top_k + 2 if question["kind"] == "temporal" else top_k
        results = engine.recall(question["q"], top_k=k)
        if question["kind"] == "temporal":

            def event_date(result) -> str:
                match = re.search(r"\d{4}-\d{2}-\d{2}", result.item.content)
                return (
                    match.group(0)
                    if match
                    else result.item.created_at.date().isoformat()
                )

            results = sorted(results, key=event_date)
            contexts[question["q"]] = [
                f"{event_date(r)}: {r.item.content}" for r in results
            ]
        else:
            contexts[question["q"]] = [r.item.content for r in results]
    engine.close()
    return contexts


def _mem0_contexts(dataset: dict, questions: list[dict], top_k: int) -> dict:
    from mem0 import Memory

    db_path = os.path.join(_WORK, "mem0db")
    if os.path.isdir(db_path):
        shutil.rmtree(db_path)
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
                "collection_name": "mem0_matrix_bench",
                "path": db_path,
            },
        },
        "history_db_path": os.path.join(_WORK, "mem0_matrix_history.db"),
    }
    mem = Memory.from_config(cfg)
    for memory in dataset["facts"] + dataset["events"]:
        mem.add(memory["content"], user_id="u1", infer=False)
    contexts = {}
    for question in questions:
        resp = mem.search(
            question["q"], filters={"user_id": "u1"}, limit=top_k
        )
        contexts[question["q"]] = [
            r.get("memory", "") for r in resp.get("results", [])
        ]
    return contexts


def _cognitive_contexts(dataset: dict, questions: list[dict], top_k: int) -> dict:
    req_file = os.path.join(_WORK, "cm_contexts_request.json")
    out_file = os.path.join(_WORK, "cm_contexts_result.json")
    with open(req_file, "w", encoding="utf-8") as handle:
        json.dump(
            {"dataset": dataset, "questions": questions, "top_k": top_k},
            handle,
            ensure_ascii=False,
        )
    candidates = [r"C:\Python314\python.exe", sys.executable]
    system_python = sys.executable
    for cand in candidates:
        if os.path.exists(cand):
            system_python = cand
            break
    runner = os.path.join(_BENCH, "official_cognitive_memory_contexts.py")
    subprocess.run(
        [system_python, runner, req_file, out_file],
        check=True,
        capture_output=True,
        text=True,
    )
    with open(out_file, encoding="utf-8") as handle:
        return json.load(handle)


def _prompt(contexts: list[str], question: str, temporal: bool) -> str:
    context = "\n".join(f"- {c}" for c in contexts)
    prompt = (
        "Answer using ONLY the memory context below. "
        "If the context lacks the answer, answer 'unknown'.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
    if temporal:
        prompt += (
            "\nThe 'next' event is the one with the earliest "
            "date strictly after the anchor date in the context."
        )
    return prompt


def run_ollama_matrix(
    contexts: dict[str, list[str]],
    questions: list[dict],
    models: list[str],
    url: str,
    timeout: int,
) -> dict[str, dict]:
    matrix: dict[str, dict] = {}
    for model in models:
        hits = 0
        details = []
        for question in questions:
            prompt = _prompt(
                contexts[question["q"]],
                question["q"],
                question["kind"] == "temporal",
            )
            start = time.perf_counter()
            try:
                answer = _generate(model, prompt, url, timeout)
            except Exception as exc:  # noqa: BLE001
                answer = f"<error: {exc}>"
            took = time.perf_counter() - start
            score = score_answer(answer, question["answer"])
            hits += int(score >= 1.0)
            details.append(
                {
                    "kind": question["kind"],
                    "question": question["q"],
                    "answer": answer,
                    "expected": question["answer"],
                    "score": round(score, 3),
                    "seconds": round(took, 2),
                }
            )
            print(
                f"  [{model}] {question['q'][:42]:44s} "
                f"score={score:.2f} ({took:.1f}s)",
                flush=True,
            )
        matrix[model] = {
            "accuracy": round(hits / len(questions), 3),
            "avg_seconds": round(
                sum(d["seconds"] for d in details) / len(details), 2
            ),
            "details": details,
        }
    return matrix


def score_codex(questions: list[dict]) -> dict:
    answers_file = os.path.join(_WORK, "codex_project_answers.json")
    with open(answers_file, encoding="utf-8") as handle:
        answers = json.load(handle)
    matrix = {}
    for project, rows in answers.items():
        hits = 0
        details = []
        for question in questions:
            answer = rows.get(question["q"], "")
            score = score_answer(answer, question["answer"])
            hits += int(score >= 1.0)
            details.append(
                {
                    "kind": question["kind"],
                    "question": question["q"],
                    "answer": answer,
                    "expected": question["answer"],
                    "score": round(score, 3),
                }
            )
        matrix[project] = {
            "accuracy": round(hits / len(questions), 3),
            "details": details,
        }
    return matrix


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--projects",
        nargs="+",
        default=["mnemosis", "mem0", "cognitive"],
    )
    parser.add_argument(
        "--models",
        nargs="+",
        default=["qwen3-vl:8b", "qwen2.5-vl", "qwen2.5:3b"],
    )
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--score-codex", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_WORK, "model_project_matrix.json"),
    )
    args = parser.parse_args()

    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    questions = select_questions(dataset)

    if args.score_codex:
        matrix = score_codex(questions)
        with open(args.out, "w", encoding="utf-8") as handle:
            json.dump(matrix, handle, ensure_ascii=False, indent=2)
        print(json.dumps(matrix, ensure_ascii=False, indent=2))
        return 0

    contexts = {}
    for project in args.projects:
        print(f"== building contexts: {project} ==", flush=True)
        if project == "mnemosis":
            contexts[project] = _mnemosis_contexts(dataset, questions, 3)
        elif project == "mem0":
            contexts[project] = _mem0_contexts(dataset, questions, 3)
        elif project == "cognitive":
            contexts[project] = _cognitive_contexts(dataset, questions, 3)
        else:
            raise SystemExit(f"unknown project: {project}")

    pending = os.path.join(_WORK, "codex_project_answers.json")
    if os.path.exists(pending):
        with open(pending, encoding="utf-8") as handle:
            codex_answers = json.load(handle)
    else:
        codex_answers = {}
    for project, ctx in contexts.items():
        codex_answers.setdefault(project, {})
        for question in questions:
            codex_answers[project].setdefault(question["q"], "")
    with open(pending, "w", encoding="utf-8") as handle:
        json.dump(codex_answers, handle, ensure_ascii=False, indent=2)

    # Warm up the first model so the timed questions are not measured while
    # Ollama is still loading weights (loading errors otherwise appear as
    # fast score=0 rows).
    print(f"== warmup {args.models[0]} ==", flush=True)
    try:
        _generate(args.models[0], "Say OK.", args.url, args.timeout, max_tokens=4)
    except Exception as exc:  # noqa: BLE001
        print("warmup failed:", exc, flush=True)

    matrix = {}
    for project in args.projects:
        print(f"== LLM x {project} ==", flush=True)
        matrix[project] = run_ollama_matrix(
            contexts[project], questions, args.models, args.url, args.timeout
        )
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print(json.dumps(matrix, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
