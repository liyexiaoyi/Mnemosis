"""Re-run the Mnemosis side of the game-dev spot-check (round 254).

After the concept-coverage retrieval fix, rebuild only the Mnemosis
contexts and re-answer with cloud qwen3.7-plus and local qwen2.5:3b.
mem0 / cognitive contexts and answers stay untouched.
"""

from __future__ import annotations

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from game_dev_spot_bench import (
    QUESTIONS,
    _mnemosis_contexts,
    cloud_generate,
    hit,
    local_generate,
    score_answer,
)


def _dim_totals(pairs: dict[str, bool]) -> tuple[int, dict[str, float]]:
    by_dim: dict[str, list[int]] = {}
    for question in QUESTIONS:
        by_dim.setdefault(question["dim"], []).append(
            1 if pairs[question["q"]] else 0
        )
    total = sum(value for values in by_dim.values() for value in values)
    per_dim = {
        dim: round(sum(values) / len(values), 3)
        for dim, values in by_dim.items()
    }
    return total, per_dim


def main() -> int:
    path = os.path.join(_WORK, "gamedev_spot.json")
    spot = json.load(open(path, encoding="utf-8"))
    contexts = _mnemosis_contexts()
    spot["contexts"]["mnemosis"] = contexts
    pairs = {q["q"]: hit(contexts[q["q"]], q) for q in QUESTIONS}
    total, per_dim = _dim_totals(pairs)
    spot["retrieval"]["mnemosis"] = {"total": total, "per_dim": per_dim}
    print("mnemosis retrieval:", total, per_dim)

    for key, generator in (
        ("answers_cloud", cloud_generate),
        ("answers_local", local_generate),
    ):
        answers = {}
        for question in QUESTIONS:
            prompt = (
                "只根据下面的记忆回答，不要编造。"
                "如果记忆里没有答案，就回答：不知道。\n\n"
                "记忆：\n"
                + "\n".join(
                    f"- {text}" for text in contexts[question["q"]]
                )
                + f"\n\n问题：{question['q']}"
            )
            try:
                answers[question["q"]] = generator(prompt)
            except Exception as exc:  # noqa: BLE001
                answers[question["q"]] = f"<error: {exc}>"
            print(f"  [{key}] {question['q'][:24]} done", flush=True)
        spot[key]["mnemosis"] = answers
        acc_pairs = {
            q["q"]: score_answer(answers[q["q"]], q) for q in QUESTIONS
        }
        acc_total, acc_per_dim = _dim_totals(acc_pairs)
        spot["accuracy_" + key.split("_")[1]]["mnemosis"] = {
            "total": acc_total,
            "per_dim": acc_per_dim,
        }
        print("mnemosis", key, acc_total, acc_per_dim)

    json.dump(
        spot,
        open(path, "w", encoding="utf-8"),
        ensure_ascii=False,
        indent=2,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
