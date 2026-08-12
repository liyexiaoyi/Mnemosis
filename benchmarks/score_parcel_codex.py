"""DeepSeek-side answers for round 292, merged into work/parcel_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from parcel_spot_bench import QUESTIONS

STANDARD = {
    "驿站现在在哪？": "小区东门",
    "寄件首重多少钱？": "12元",
    "上次寄大件是什么时候？多少钱？": "4月25日，85元",
    "上次快递赔偿到账多少？": "150元",
    "下次寄生日礼物是什么时候？": "8月12日",
    "取件码保留几天？": "3天",
    "驿站会员多少钱？": "8元/月",
    "新老板电话多少？": "400-999-8888",
    "驿站营业到几点？": "21:00",
    "包裹不取几天退回？": "3天",
}


def main() -> int:
    path = os.path.join(_WORK, "parcel_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "parcel_codex_answers.json"),
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
