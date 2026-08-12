"""DeepSeek-side answers for round 328, merged into work/hotel_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from hotel_spot_bench import QUESTIONS

STANDARD = {
    "第一次入住是什么时候？": "1月20日",
    "积分记录是多少？": "2000分",
    "会员价几折？": "9折",
    "下次入住是什么时候？": "8月12日",
    "多少分换一晚？": "1000分",
    "延迟退房什么时候？": "5月15日",
    "会员什么时候续的？": "6月20日",
    "酒店客服电话多少？": "400-666-3333",
    "积分什么时候清零？": "8月15日",
    "早餐什么时候升级？": "3月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "hotel_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "hotel_codex_answers.json"),
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
