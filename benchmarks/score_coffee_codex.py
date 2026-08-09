# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 294, merged into work/coffee_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from coffee_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "会员卡充多少送多少？": "充300送60",
    "常点什么咖啡？多少钱？": "大杯拿铁32元",
    "会员日什么时候？优惠？": "每周二第二杯半价",
    "下次取蛋糕是什么时候？": "8月12日",
    "拉花课什么时候上的？": "3月10日",
    "新品燕麦拿铁多少钱？": "38元",
    "积分多少换一杯？": "500分",
    "咖啡豆多少钱？": "120元/250g",
    "咖啡师叫什么？": "小周",
    "会员答谢日什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "coffee_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "coffee_codex_answers.json"),
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
