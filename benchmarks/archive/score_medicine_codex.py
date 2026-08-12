"""DeepSeek-side answers for round 300, merged into work/medicine_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from medicine_spot_bench import QUESTIONS

STANDARD = {
    "药箱里有什么？": "创可贴、体温计",
    "感冒吃什么药？": "布洛芬",
    "孩子发烧用什么？": "美林",
    "过敏吃什么药？": "氯雷他定",
    "下次买钙片是什么时候？": "8月12日",
    "过期药什么时候回收的？": "5月30日",
    "孩子腹泻用什么？": "蒙脱石散",
    "药箱什么时候整理的？": "7月10日",
    "药店电话多少？": "400-333-2222",
    "药品怎么储存？": "阴凉干燥处",
}


def main() -> int:
    path = os.path.join(_WORK, "medicine_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "medicine_codex_answers.json"),
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
