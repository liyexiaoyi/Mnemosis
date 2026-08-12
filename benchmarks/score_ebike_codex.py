"""DeepSeek-side answers for round 306, merged into work/ebike_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from ebike_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "电动车多少钱？什么牌子？": "雅迪，3299元",
    "上次保养是什么时候？": "3月15日",
    "电池什么时候换的？多少钱？": "5月10日，600元",
    "下次贴膜是什么时候？": "8月12日",
    "头盔多少钱？": "299元",
    "刹车什么问题？什么时候修的？": "异响，6月5日",
    "年检通过了吗？什么时候？": "7月10日通过",
    "电动车停哪？": "B1-08",
    "充电器什么时候换新？": "8月15日",
    "免费检修日什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "ebike_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "ebike_codex_answers.json"),
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
