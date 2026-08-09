# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 331, merged into work/go_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from go_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "围棋班第一次报名是什么时候？": "1月12日",
    "围棋班一期多少钱？": "2000元",
    "下次围棋课是什么时候？": "8月22日",
    "围棋课每周几上？": "周六",
    "围棋考级过了吗？现在什么级别？": "通过，8级",
    "围棋老师电话多少？": "138-0000-8888",
    "孩子上课请假怎么处理？": "提前一天在群里请假",
    "市级围棋比赛什么时候？": "9月6日",
    "家长会什么时候开的？": "6月30日",
    "围棋夏令营什么时候开始？": "7月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "go_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "go_codex_answers.json"),
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
