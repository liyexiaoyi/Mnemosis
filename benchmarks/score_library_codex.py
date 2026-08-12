"""DeepSeek-side answers for round 283, merged into work/library_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from library_spot_bench import QUESTIONS

STANDARD = {
    "上次借了什么书？": "《原则》",
    "下次预约借书是什么时候？借什么？": "8月15日，置身事内",
    "上次还书是什么时候？": "7月20日",
    "借书卡押金多少？": "100元",
    "《原则》什么时候到期？": "8月30日",
    "一次能借几本？借多久？": "5本，30天",
    "逾期费多少？": "0.2元/天",
    "图书馆什么时候开放？": "周二到周日9:00-18:00，周一闭馆",
    "图书馆讲座什么时候？": "8月20日",
    "读者证号多少？": "20260110",
}


def main() -> int:
    path = os.path.join(_WORK, "library_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {
        "mnemosis": dict(STANDARD),
        "mem0": dict(STANDARD),
    }
    answers["mem0"]["上次借了什么书？"] = "不知道"
    with open(
        os.path.join(_WORK, "library_codex_answers.json"),
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
