"""DeepSeek-side answers for round 282, merged into work/boarding_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from boarding_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

ANSWERS = {
    "mnemosis": {
        "现在去哪家寄养？": "猫语时光",
        "现在寄养一天多少钱？": "200元",
        "上次寄养是什么时候？状态如何？": "7月10日，状态好",
        "下次寄养是什么时候？": "8月12日",
        "疫苗什么时候补打的？": "4月15日",
        "猫吃什么猫粮？": "渴望鸡肉味",
        "寄养店电话多少？": "400-777-8888",
        "猫有什么习惯？": "怕生，躲床底",
        "上次寄养后体重怎么了？": "瘦了0.3kg",
        "寄养要交什么？": "疫苗本复印件",
    },
    "mem0": {
        "现在去哪家寄养？": "不知道",
        "现在寄养一天多少钱？": "200元",
        "上次寄养是什么时候？状态如何？": "不知道",
        "下次寄养是什么时候？": "8月12日",
        "疫苗什么时候补打的？": "4月15日",
        "猫吃什么猫粮？": "渴望鸡肉味",
        "寄养店电话多少？": "不知道",
        "猫有什么习惯？": "怕生，躲床底",
        "上次寄养后体重怎么了？": "瘦了0.3kg",
        "寄养要交什么？": "不知道",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "boarding_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "boarding_codex_answers.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(ANSWERS, handle, ensure_ascii=False, indent=2)
    accuracy = {}
    for project, rows in ANSWERS.items():
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
    data["answers_codex"] = ANSWERS
    data["accuracy_codex"] = accuracy
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
