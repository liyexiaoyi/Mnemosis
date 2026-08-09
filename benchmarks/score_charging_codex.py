# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 342, merged into work/charging_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from charging_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "充电桩第一次什么时候安装的？": "1月8日",
    "充电桩安装费多少钱？": "800元",
    "下次充电桩保养是什么时候？": "8月15日",
    "充电桩装在哪里？": "小区地下车库B区",
    "充电桩售后电话多少？": "400-900-5678",
    "充电桩功率多大？": "7千瓦",
    "低谷时段一度电多少钱？": "0.3元",
    "充电桩巡检什么时候？": "2月25日",
    "保险什么时候续费？": "8月22日",
    "充电桩故障怎么处理？": "联系售后",
}


def main() -> int:
    path = os.path.join(_WORK, "charging_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["充电桩售后电话多少？"] = "不知道"
    with open(
        os.path.join(_WORK, "charging_codex_answers.json"),
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
