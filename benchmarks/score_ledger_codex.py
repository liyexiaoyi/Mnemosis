# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 303, merged into work/ledger_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from ledger_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "现在每月预算多少？": "6500元",
    "哪个月超预算了？": "3月",
    "半年总支出多少？": "3.6万",
    "下次做预算是什么时候？": "8月12日",
    "上次对账是什么时候？": "5月10日",
    "理财复盘什么时候？": "7月10日",
    "记账分几类？": "餐饮、交通、住房",
    "每天几点记账？": "晚9点",
    "用什么记账软件？": "随手记",
    "什么时候交房租？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "ledger_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "ledger_codex_answers.json"),
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
