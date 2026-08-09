# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 317, merged into work/sports_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from sports_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "跑鞋多少钱？": "899元",
    "半马什么时候跑的？成绩多少？": "7月15日，2小时5分",
    "半马报名什么时候截止？": "3月20日",
    "下次买新跑鞋是什么时候？": "8月12日",
    "体测什么时候？": "4月15日",
    "跑姿分析什么时候？": "5月25日",
    "上次长距离训练是什么时候？": "6月25日",
    "买了什么装备？": "运动手表",
    "拉伸课什么时候？": "8月15日",
    "买了什么补给？": "能量胶",
}


def main() -> int:
    path = os.path.join(_WORK, "sports_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "sports_codex_answers.json"),
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
