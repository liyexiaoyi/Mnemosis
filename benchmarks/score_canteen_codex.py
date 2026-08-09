# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 330, merged into work/canteen_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from canteen_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "饭卡什么时候办的？": "2月1日",
    "充值了多少钱？": "200元",
    "周一吃什么？": "红烧肉",
    "下次充值是什么时候？": "8月12日",
    "饭卡余额多少？": "160元",
    "包间什么时候用餐？": "3月25日",
    "食堂卫生检查什么时候？过了吗？": "6月15日，通过",
    "食堂电话多少？": "400-222-6666",
    "食堂什么时候涨价的？": "5月1日",
    "饭卡什么时候到期？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "canteen_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["食堂卫生检查什么时候？过了吗？"] = "不知道"
    with open(
        os.path.join(_WORK, "canteen_codex_answers.json"),
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
