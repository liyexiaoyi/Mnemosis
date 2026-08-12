"""DeepSeek-side answers for round 327, merged into work/massage_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from massage_spot_bench import QUESTIONS

STANDARD = {
    "第一次按摩是什么时候？": "1月20日",
    "按摩卡多少钱一次？": "120元",
    "理疗什么时候？": "2月25日",
    "下次按摩是什么时候？": "8月12日",
    "拔罐什么时候？": "3月25日",
    "艾灸什么时候？": "4月15日",
    "刮痧什么时候？": "6月15日",
    "正骨什么时候？": "7月15日",
    "理疗店电话多少？": "400-777-8888",
    "按摩要注意什么？": "饭后一小时",
}


def main() -> int:
    path = os.path.join(_WORK, "massage_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "massage_codex_answers.json"),
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
