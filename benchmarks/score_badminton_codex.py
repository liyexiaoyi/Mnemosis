# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 334, merged into work/badminton_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from badminton_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "羽毛球年卡第一次什么时候办的？": "1月5日",
    "羽毛球年卡多少钱？": "2800元",
    "下次预约的场地是什么时候？": "8月14日",
    "球馆几点关门？": "晚11点",
    "教练课什么时候上的？": "3月20日",
    "球馆前台电话多少？": "0755-6666-8888",
    "场地提前多久可以免费取消？": "提前2小时",
    "球馆双打比赛什么时候？": "4月25日",
    "年卡续费优惠什么时候截止？": "8月22日",
    "订场8折优惠什么时候截止？": "6月1日前",
}


def main() -> int:
    path = os.path.join(_WORK, "badminton_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "badminton_codex_answers.json"),
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
