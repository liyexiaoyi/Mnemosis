# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 319, merged into work/neighbor_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from neighbor_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "认识了哪位邻居？": "张阿姨",
    "邻居帮了什么忙？": "收快递",
    "邻里聚餐什么时候？": "3月25日",
    "下次读书会是什么时候？": "8月12日",
    "业主大会什么时候？": "4月15日",
    "社区义诊什么时候？": "5月30日",
    "跳蚤市场摆摊什么时候？": "6月25日",
    "小区清洁日什么时候？": "7月25日",
    "物业电话多少？": "400-555-1111",
    "业主什么时候缴费？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "neighbor_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "neighbor_codex_answers.json"),
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
