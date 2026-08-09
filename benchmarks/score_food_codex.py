# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 270, merged into work/food_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from food_spot_bench import QUESTIONS  # noqa: E402


ANSWERS = {
    "mnemosis": {
        "转让费多少？月租多少？": "转让费8万，月租6000",
        "食品经营许可证什么时候拿到的？": "2月1日",
        "招牌牛肉面多少钱？豌杂面呢？": "牛肉面18元，豌杂面22元",
        "最近一次盘点牛肉面日销多少碗？": "120碗",
        "美团抽成是多少？": "15%",
        "上次卫生检查是什么时候？结果如何？": "4月25日，通过",
        "下次更换燃气软管是什么时候？": "8月5日",
        "营业时间是几点到几点？哪天休息？": "早8点到晚10点，周一休息",
        "牛肉找谁进货？": "老李",
        "隔壁奶茶店为什么没接？": "资金不够",
    },
    "mem0": {
        "转让费多少？月租多少？": "转让费8万，月租6000",
        "食品经营许可证什么时候拿到的？": "2月1日",
        "招牌牛肉面多少钱？豌杂面呢？": "牛肉面18元，豌杂面22元",
        "最近一次盘点牛肉面日销多少碗？": "120碗",
        "美团抽成是多少？": "15%",
        "上次卫生检查是什么时候？结果如何？": "4月25日，通过",
        "下次更换燃气软管是什么时候？": "8月5日",
        "营业时间是几点到几点？哪天休息？": "早8点到晚10点，周一休息",
        "牛肉找谁进货？": "老李",
        "隔壁奶茶店为什么没接？": "资金不够",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "food_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "food_codex_answers.json"),
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
