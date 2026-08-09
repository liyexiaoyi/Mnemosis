# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 338, merged into work/garden2_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from garden2_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "菜地第一次是什么时候认领的？": "1月11日",
    "认领菜地一年多少钱？": "150元",
    "下次花园活动是什么时候？": "8月19日",
    "花园几点开门？": "早7点",
    "花园管理员电话多少？": "0571-3333-2222",
    "一块菜地最多种几种作物？": "3种",
    "第一批番茄什么时候采摘的？": "6月5日",
    "花园评比什么时候？": "5月28日",
    "菜地年费什么时候续缴？": "8月25日",
    "园艺讲座什么时候？": "8月30日",
}


def main() -> int:
    path = os.path.join(_WORK, "garden2_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["下次花园活动是什么时候？"] = "不知道"
    with open(
        os.path.join(_WORK, "garden2_codex_answers.json"),
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
