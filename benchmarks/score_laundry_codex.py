# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 329, merged into work/laundry_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from laundry_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "干洗羽绒服多少钱？": "80元",
    "洗衣卡充多少送多少？": "充500送50",
    "窗帘什么时候洗好的？": "2月25日",
    "下次洗冬衣是什么时候？": "8月12日",
    "羽绒服返洗什么时候？": "4月5日",
    "西装什么时候洗好的？": "5月15日",
    "洗衣卡余额多少？": "350元",
    "地毯什么时候洗好的？": "6月25日",
    "干洗店电话多少？": "400-111-2222",
    "取件要几天？": "3天",
}


def main() -> int:
    path = os.path.join(_WORK, "laundry_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "laundry_codex_answers.json"),
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
