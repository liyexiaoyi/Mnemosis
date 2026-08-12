"""Round-365 local-model re-test: same chaos contexts, local answer models.

Answers the round-365 chaos spot-check questions from the exact contexts
retrieved by Mnemosis and mem0, using qwen2.5:3b and gemma3:12b (Ollama).
"""

from __future__ import annotations

import importlib
import json
import os
import sys
import urllib.request

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit

OLLAMA_URL = "http://127.0.0.1:11434"
MODELS = ["qwen2.5:3b", "gemma3:12b"]


def _generate(model: str, prompt: str) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", "").strip()


def _prompt(rows: list[str], question: str) -> str:
    return (
        "只根据下面的记忆回答，不要编造。"
        "如果记忆里没有答案，就回答：不知道。\n\n"
        "记忆：\n"
        + "\n".join(f"- {text}" for text in rows)
        + f"\n\n问题：{question}"
    )


def main() -> int:
    domain = sys.argv[1] if len(sys.argv) > 1 else "chaos"
    bench = importlib.import_module(f"{domain}_spot_bench")
    QUESTIONS = bench.QUESTIONS
    path = os.path.join(_WORK, f"{domain}_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    summary = {}
    for model in MODELS:
        answers = {}
        for project in ("mnemosis", "mem0"):
            answers[project] = {}
            for question in QUESTIONS:
                rows = data["contexts"][project][question["q"]]
                try:
                    answers[project][question["q"]] = _generate(
                        model, _prompt(rows, question["q"])
                    )
                except Exception as exc:  # noqa: BLE001
                    answers[project][question["q"]] = f"<error: {exc}>"
                print(
                    f"  [{model}][{project}] {question['q'][:18]} done",
                    flush=True,
                )
        accuracy = {}
        for project, rows in answers.items():
            total = 0
            per_dim: dict[str, list[int]] = {}
            for question in QUESTIONS:
                ok = hit([rows[question["q"]]], question)
                total += 1 if ok else 0
                per_dim.setdefault(question["dim"], []).append(1 if ok else 0)
            accuracy[project] = {
                "total": total,
                "per_dim": {
                    dim: round(sum(values) / len(values), 3)
                    for dim, values in per_dim.items()
                },
            }
            print("accuracy_local", model, project, total)
        summary[model] = {
            "answers": answers,
            "accuracy": accuracy,
        }
    out = os.path.join(_WORK, f"{domain}_local_round365.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)
    print("written:", out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
