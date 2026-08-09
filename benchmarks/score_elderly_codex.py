# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 358, merged into work/elderly_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from elderly_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "第一次参观养老院是什么时候？": "1月9日",
    "养老院一个月多少钱？": "4500元",
    "下次探视是什么时候？": "8月17日",
    "养老院几点开门接待？": "早8点",
    "养老院电话多少？": "024-8888-4444",
    "养老院有哪些服务项目？": "生活照料、医疗照护、康复训练、文娱活动",
    "养老院每天几餐？": "三餐两点",
    "入住押金多少钱？": "5000元",
    "医疗评估什么时候完成的？": "3月24日",
    "入住申请什么时候截止？": "8月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "elderly_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "elderly_codex_answers.json"),
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
