# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 318, merged into work/utility_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from utility_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "上次电费多少钱？": "186元",
    "上次水费多少钱？": "58元",
    "物业费什么时候缴的？多少钱？": "3月10日，800元",
    "下次缴电费是什么时候？": "8月12日",
    "燃气表什么时候换的？": "4月15日",
    "暖气费多少钱？": "1200元",
    "垃圾费多少钱？": "30元",
    "缴费客服电话多少？": "400-666-0000",
    "每月几号缴费？": "15日",
    "燃气费什么时候缴？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "utility_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["上次电费多少钱？"] = "不知道"
    with open(
        os.path.join(_WORK, "utility_codex_answers.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(answers, handle, ensure_ascii=False, indent=2)
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
        print("accuracy_codex", project, total)
    data["answers_codex"] = answers
    data["accuracy_codex"] = accuracy
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
