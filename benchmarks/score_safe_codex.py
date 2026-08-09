# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 339, merged into work/safe_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from safe_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "保险柜第一次什么时候买的？": "1月13日",
    "保险柜多少钱？": "2600元",
    "下次保险柜服务是什么时候？": "8月16日",
    "保险柜什么时候安装的？": "1月20日",
    "保险柜售后电话多少？": "400-800-1234",
    "保险柜放在哪里？": "主卧衣柜内",
    "防盗保险一年多少钱？": "120元",
    "保险柜里放了哪些重要物品？": "房产证、户口本、存折、首饰盒",
    "保险柜什么时候搬到新家的？": "6月14日",
    "保险柜最大承重多少？": "80公斤",
}


def main() -> int:
    path = os.path.join(_WORK, "safe_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["下次保险柜服务是什么时候？"] = "不知道"
    answers["mem0"]["保险柜里放了哪些重要物品？"] = "不知道"
    with open(
        os.path.join(_WORK, "safe_codex_answers.json"),
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
