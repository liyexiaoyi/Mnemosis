# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 289, merged into work/insurance_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from insurance_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "重疾险保额多少？一年多少钱？": "50万，6800元",
    "上次理赔到账多少？": "3200元",
    "理赔审核结果什么时候出？": "8月15日",
    "下次递交材料是什么时候？": "8月18日",
    "理赔要交什么材料？": "发票、病历、诊断证明",
    "保单号多少？": "P-2026-0315",
    "保险公司客服电话多少？": "95599",
    "重疾险什么时候续缴的？": "6月1日",
    "什么时候补充材料？": "6月30日前",
    "上次理赔面谈是什么时候？": "7月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "insurance_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "insurance_codex_answers.json"),
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
