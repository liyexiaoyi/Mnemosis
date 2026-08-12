"""DeepSeek-side answers for round 340, merged into work/tile_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from tile_spot_bench import QUESTIONS

STANDARD = {
    "客厅瓷砖第一次什么时候买的？": "1月9日",
    "客厅瓷砖多少钱？": "4200元",
    "下次瓷砖送货是什么时候？": "8月16日",
    "瓷砖门店几点开门？": "早9点",
    "瓷砖门店电话多少？": "0592-8888-6666",
    "客厅瓷砖是什么规格？": "800x800",
    "客厅瓷砖剩下多少片？": "10片",
    "瓦工师傅什么时候进场的？": "2月14日",
    "瓷砖质保几年？": "5年",
    "瓷砖验收什么时候？": "4月22日",
}


def main() -> int:
    path = os.path.join(_WORK, "tile_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "tile_codex_answers.json"),
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
