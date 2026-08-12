"""Compare Mnemosis against local LLMs (Ollama) on a small memory benchmark.

Conditions:
  1. mnemosis_only        - does Mnemosis retrieval surface the right memory?
  2. llm_alone            - can the LLM answer from parametric knowledge alone?
  3. llm_with_mnemosis    - LLM answers grounded in Mnemosis recall results.

Usage:
    python benchmarks/compare_with_models.py --models gemma3:12b qwen2.5-vl:latest
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from bench_utils import pin_local_src

pin_local_src()

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

BENCHMARK = {
    "memories": [
        {
            "content": "Alice prefers dark mode over light mode.",
            "kind": "semantic",
            "cues": ["alice", "preference"],
        },
        {
            "content": "Alice's birthday is March 14.",
            "kind": "semantic",
            "cues": ["alice", "birthday"],
        },
        {
            "content": "Bob is allergic to peanuts.",
            "kind": "semantic",
            "cues": ["bob", "allergy"],
        },
        {
            "content": "The team uses Python and SQLite for the memory project.",
            "kind": "semantic",
            "cues": ["team", "stack"],
        },
        {
            "content": "Alice said the release deadline moved to Friday.",
            "kind": "episodic",
            "cues": ["alice", "deadline"],
        },
        {
            "content": "用户喜欢在技术讨论中使用中文。",
            "kind": "semantic",
            "cues": ["用户", "语言"],
        },
    ],
    "questions": [
        {
            "q": "What display mode does Alice prefer?",
            "answer": "dark mode",
            "memory": 0,
        },
        {"q": "When is Alice's birthday?", "answer": "march 14", "memory": 1},
        {"q": "What is Bob allergic to?", "answer": "peanuts", "memory": 2},
        {
            "q": "Which languages does the team use?",
            "answer": "python sqlite",
            "memory": 3,
        },
        {
            "q": "What day did the release deadline move to?",
            "answer": "friday",
            "memory": 4,
        },
        {
            "q": "用户喜欢用什么语言进行技术讨论？",
            "answer": "中文",
            "memory": 5,
        },
    ],
}


def ollama_generate(
    model: str, prompt: str, url: str = "http://127.0.0.1:11434", timeout: int = 180
) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        data = json.loads(response.read().decode("utf-8"))
    return data.get("response", "").strip()


def score_answer(answer: str, expected: str) -> float:
    """Fraction of expected tokens present in the model answer."""
    lowered = answer.lower()
    tokens = [t for t in expected.lower().split() if t]
    if not tokens:
        return 1.0 if answer.strip() else 0.0
    hits = sum(1 for token in tokens if token in lowered)
    return hits / len(tokens)


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for memory in BENCHMARK["memories"]:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.7,
        )
    return engine


def run_mnemosis_only() -> dict:
    engine = build_engine()
    hits = 0
    details = []
    for question in BENCHMARK["questions"]:
        results = engine.recall(question["q"], top_k=5)
        contents = [r.item.content for r in results]
        target = BENCHMARK["memories"][question["memory"]]["content"]
        hit = target in contents
        hits += int(hit)
        details.append(
            {"question": question["q"], "hit": hit, "top": contents[:3]}
        )
    return {
        "approach": "mnemosis_only",
        "model": "-",
        "accuracy": round(hits / len(BENCHMARK["questions"]), 3),
        "avg_seconds": None,
        "details": details,
    }


def run_llm_condition(
    engine: MemoryEngine, model: str, condition: str, url: str, timeout: int
) -> dict:
    hits = 0
    elapsed = 0.0
    details = []
    for question in BENCHMARK["questions"]:
        if condition == "llm_alone":
            prompt = (
                "Answer with only the requested fact. "
                "If you do not know, answer 'unknown'.\n"
                f"Question: {question['q']}"
            )
        else:
            results = engine.recall(question["q"], top_k=3)
            context = "\n".join(f"- {r.item.content}" for r in results)
            prompt = (
                "Answer using ONLY the memory context below. "
                "If the context lacks the answer, answer 'unknown'.\n\n"
                f"Context:\n{context}\n\n"
                f"Question: {question['q']}"
            )
        start = time.perf_counter()
        try:
            answer = ollama_generate(model, prompt, url, timeout)
        except Exception as exc:  # noqa: BLE001 - record and continue
            answer = f"<error: {exc}>"
        took = time.perf_counter() - start
        elapsed += took
        score = score_answer(answer, question["answer"])
        hits += 1 if score >= 1.0 else 0
        details.append(
            {
                "question": question["q"],
                "answer": answer,
                "expected": question["answer"],
                "score": round(score, 3),
                "seconds": round(took, 2),
            }
        )
        print(
            f"  [{condition}] {question['q'][:38]:40s} "
            f"score={score:.2f} ({took:.1f}s)",
            flush=True,
        )
    total = len(BENCHMARK["questions"])
    return {
        "approach": condition,
        "model": model,
        "accuracy": round(hits / total, 3),
        "avg_seconds": round(elapsed / total, 2),
        "details": details,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models",
        nargs="+",
        default=["gemma3:12b", "qwen2.5-vl:latest"],
        help="Ollama model names to compare",
    )
    parser.add_argument("--url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            f"compare_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json",
        ),
    )
    args = parser.parse_args()

    engine = build_engine()
    rows = [run_mnemosis_only()]

    for model in args.models:
        print(f"== {model} ==", flush=True)
        for condition in ("llm_alone", "llm_with_mnemosis"):
            rows.append(
                run_llm_condition(engine, model, condition, args.url, args.timeout)
            )

    print("\n== summary ==")
    print(f"{'approach':20s} {'model':16s} {'accuracy':>8s} {'avg s':>8s}")
    for row in rows:
        avg = "-" if row["avg_seconds"] is None else f"{row['avg_seconds']:.1f}"
        print(
            f"{row['approach']:20s} {row['model']:16s} "
            f"{row['accuracy']:>8.3f} {avg:>8s}"
        )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
    print(f"\nresults saved to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

