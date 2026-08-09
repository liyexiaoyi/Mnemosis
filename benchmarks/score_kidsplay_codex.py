# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 348, merged into work/kidsplay_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from kidsplay_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "儿童乐园年卡第一次什么时候办的？": "1月4日",
    "年卡多少钱？": "1999元",
    "下次游玩是什么时候？": "8月17日",
    "乐园几点关门？": "晚8点",
    "儿童乐园电话多少？": "0791-8888-9999",
    "乐园有哪些游乐项目？": "海洋球池、蹦床、沙池、小火车",
    "消费多少可以免费停车2小时？": "100元",
    "几岁以下需要家长陪同？": "3岁以下",
    "生日派对什么时候办的？": "2月15日",
    "年卡续卡优惠什么时候截止？": "8月28日",
}


def main() -> int:
    path = os.path.join(_WORK, "kidsplay_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "kidsplay_codex_answers.json"),
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
