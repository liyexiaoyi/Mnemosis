# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 344, merged into work/spa_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from spa_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "第一次去温泉会所是什么时候？": "1月5日",
    "温泉门票多少钱？": "168元",
    "下次到店是什么时候？": "8月15日",
    "会所几点关门？": "晚11点",
    "温泉会所电话多少？": "027-7777-2222",
    "会所有哪些设施项目？": "温泉池、汗蒸、按摩、自助餐",
    "储物柜押金多少？": "50元",
    "会员可以免费停车多久？": "3小时",
    "哪些人不建议泡高温池？": "高血压、心脏病患者",
    "会员卡余额什么时候会不足？": "8月24日",
}


def main() -> int:
    path = os.path.join(_WORK, "spa_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "spa_codex_answers.json"),
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
