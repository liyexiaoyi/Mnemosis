# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 321, merged into work/gymgear_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from gymgear_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "买了什么健身器材？": "弹力带",
    "跑步机什么时候买的？": "2月1日",
    "跑步机什么时候保养的？": "3月15日",
    "下次买新跑步机是什么时候？": "8月12日",
    "哑铃什么时候换新的？": "4月5日",
    "体脂秤什么时候校准的？": "5月15日",
    "跑步机什么时候检修的？": "6月25日",
    "瑜伽课什么时候？": "7月25日",
    "器材店电话多少？": "400-222-9999",
    "什么时候换跑步机油？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "gymgear_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["买了什么健身器材？"] = "不知道"
    with open(
        os.path.join(_WORK, "gymgear_codex_answers.json"),
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
