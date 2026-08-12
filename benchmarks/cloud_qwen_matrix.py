"""Model x project matrix with the CLOUD Qwen (qwen3.7-plus) and
DeepSeek V4 Flash (the agent), instead of local Ollama models.

Retrieval contexts come from the already-dumped per-project retrievers
(work/project_contexts.json). The answering model is the user-deployed
latest Qwen (qwen3.7-plus, DashScope) via the OpenAI-compatible API; the
DeepSeek V4 Flash answers are written by the agent and scored by the same
`score_answer` rule.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from compare_with_models import score_answer
from locomo_bench import generate_dataset
from model_x_project import select_questions

VISION_CONFIG = r"C:\Users\asus\plugins\image-viewer\scripts\vision_config.json"


def cloud_generate(prompt: str, max_tokens: int = 300) -> str:
    with open(VISION_CONFIG, encoding="utf-8") as handle:
        cfg = json.load(handle)
    payload = {
        "model": cfg["model"],
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }
    req = urllib.request.Request(
        cfg["base_url"] + "/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": "Bearer " + cfg["api_key"],
        },
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"].strip()


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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_WORK, "model_project_matrix_cloud.json"),
    )
    args = parser.parse_args()
    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    questions = select_questions(dataset)
    contexts = json.load(
        open(os.path.join(_WORK, "project_contexts.json"), encoding="utf-8")
    )
    matrix = {}
    for project in ("mnemosis", "mem0", "cognitive"):
        hits = 0
        details = []
        for question in questions:
            prompt = _prompt(
                contexts[project][question["q"]],
                question["q"],
                question["kind"] == "temporal",
            )
            start = time.perf_counter()
            try:
                answer = cloud_generate(prompt)
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
                f"  [qwen3.7-plus] {question['q'][:40]:42s} score={score:.2f} "
                f"({took:.1f}s)",
                flush=True,
            )
        matrix[project] = {
            "qwen3.7-plus": {
                "accuracy": round(hits / len(questions), 3),
                "details": details,
            }
        }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print(json.dumps(matrix, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
