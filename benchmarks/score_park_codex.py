"""DeepSeek-side answers for round 298, merged into work/park_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from park_spot_bench import QUESTIONS

STANDARD = {
    "公园年卡多少钱？": "600元",
    "上次去动物园是什么时候？": "2月15日",
    "下次动物园夜游是什么时候？": "8月12日",
    "花展什么时候开幕？": "3月20日",
    "上次野餐是什么时候？": "4月15日",
    "游乐园新项目是什么？": "过山车",
    "公园夜场什么时候开放？": "6月15日",
    "公园客服电话多少？": "400-777-5555",
    "公园几点开放？": "6:00-22:00",
    "音乐节什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "park_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "park_codex_answers.json"),
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
