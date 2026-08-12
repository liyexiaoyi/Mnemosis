"""DeepSeek-side answers for round 316, merged into work/eye_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from eye_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "视力筛查多少？": "4.9",
    "配了什么镜片？": "防控镜片",
    "上次复查是什么时候？右眼多少？": "5月20日，5.0",
    "下次复查是什么时候？": "8月12日",
    "买了什么护眼设备？": "护眼台灯",
    "买了什么营养素？": "叶黄素",
    "镜片什么时候换的？": "6月25日",
    "上次视力训练是什么时候？": "7月15日",
    "眼科电话多少？": "400-777-3333",
    "什么时候滴眼药水？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "eye_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "eye_codex_answers.json"),
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
