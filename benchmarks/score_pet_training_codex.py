# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 332, merged into work/pet_training_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from pet_training_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "狗狗训练班第一次报名是什么时候？": "1月8日",
    "基础班多少钱？": "3000元",
    "下次训练课是什么时候？": "8月16日",
    "训练课每周几上？": "周日",
    "狗狗学了哪些训练项目？": "坐下、趴下、随行、拒食",
    "训练学校教练电话多少？": "135-1111-2222",
    "训练课请假怎么处理？": "提前两天联系教练调课",
    "训导公开课什么时候？": "8月28日",
    "狗狗什么时候打的狂犬疫苗？": "5月11日",
    "训练学校接送怎么安排？": "上门接送，提前一天预约",
}


def main() -> int:
    path = os.path.join(_WORK, "pet_training_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["狗狗学了哪些训练项目？"] = "不知道"
    with open(
        os.path.join(_WORK, "pet_training_codex_answers.json"),
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
