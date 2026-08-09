# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 351, merged into work/familydoc_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from familydoc_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "家庭医生第一次什么时候签约的？": "1月8日",
    "家庭医生一年多少钱？": "600元",
    "下次随访是什么时候？": "8月16日",
    "家庭医生每周几门诊？": "周二、周五下午",
    "家庭医生电话多少？": "020-7777-3333",
    "家庭医生有哪些服务内容？": "健康咨询、慢病管理、用药指导、转诊协助",
    "健康档案什么时候建立的？": "3月8日",
    "转诊什么时候完成的？": "3月28日",
    "慢病管理评估什么时候？": "6月24日",
    "年费什么时候续缴？": "8月24日",
}


def main() -> int:
    path = os.path.join(_WORK, "familydoc_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "familydoc_codex_answers.json"),
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
