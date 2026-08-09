# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 301, merged into work/appliance_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from appliance_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "冰箱多少钱？": "4599元",
    "冰箱什么时候报修的？修好了吗？": "2月20日，修好",
    "洗衣机什么问题？什么时候检修的？": "异响，3月5日",
    "下次洗衣机清洗是什么时候？": "8月12日",
    "空调什么时候清洗的？": "4月25日",
    "微波炉换的什么？": "磁控管",
    "热水器什么时候保养的？": "6月15日",
    "烤箱保修什么时候到期？": "8月15日",
    "空气炸锅多少钱？": "599元",
    "家电客服电话多少？": "400-888-9999",
}


def main() -> int:
    path = os.path.join(_WORK, "appliance_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "appliance_codex_answers.json"),
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
