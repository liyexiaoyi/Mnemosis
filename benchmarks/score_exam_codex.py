# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 278, merged into work/exam_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from exam_spot_bench import QUESTIONS  # noqa: E402


ANSWERS = {
    "mnemosis": {
        "法考什么时候缴费截止？": "3月15日",
        "买了哪些教材？": "民法、刑法、民诉",
        "最近一次客观题模考多少分？": "74分",
        "客观题考了多少分？过了吗？": "182分，通过",
        "成绩什么时候公布？": "8月20日",
        "现在怎么复习？": "每天真题1套",
        "冲刺班什么时候开课？": "5月1日",
        "在哪学习？": "图书馆3楼自习室",
        "番茄钟怎么用？": "学习25分钟休息5分钟",
        "错题本放哪？": "书包",
    },
    "mem0": {
        "法考什么时候缴费截止？": "3月15日",
        "买了哪些教材？": "民法、刑法、民诉",
        "最近一次客观题模考多少分？": "74分",
        "客观题考了多少分？过了吗？": "182分，通过",
        "成绩什么时候公布？": "8月20日",
        "现在怎么复习？": "不知道",
        "冲刺班什么时候开课？": "5月1日",
        "在哪学习？": "图书馆3楼自习室",
        "番茄钟怎么用？": "学习25分钟休息5分钟",
        "错题本放哪？": "书包",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "exam_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "exam_codex_answers.json"),
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
