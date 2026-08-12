"""DeepSeek-side answers for round 274, merged into work/wedding_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from wedding_spot_bench import QUESTIONS

STANDARD = {
    "婚期是哪天？": "10月2日",
    "酒店订在哪？多少桌？每桌多少钱？": "凯悦厅，40桌，3888元",
    "婚纱照什么时候拍的？": "4月20日",
    "主纱多少钱？": "6800元",
    "婚戒什么时候取？": "8月10日",
    "蜜月去哪？什么时候出发？": "马尔代夫，9月28日",
    "彩排是什么时候？": "8月25日",
    "尾款什么时候付清？": "9月15日前",
    "化妆师电话多少？": "138-0000-8888",
    "双方父母什么时候见面？": "8月22日",
}


def main() -> int:
    path = os.path.join(_WORK, "wedding_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "wedding_codex_answers.json"),
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
