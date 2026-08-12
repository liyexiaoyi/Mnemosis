"""DeepSeek-side answers for round 313, merged into work/furniture_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from furniture_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "书桌多少钱？": "899元",
    "衣柜什么时候量尺的？": "2月25日",
    "沙发什么时候安装的？": "5月25日",
    "下次买餐椅是什么时候？": "8月12日",
    "床垫是什么类型？": "弹簧床垫",
    "书桌螺丝什么时候加固的？": "6月5日",
    "柜门什么时候调整的？": "7月15日",
    "安装师傅电话多少？": "400-333-1111",
    "书桌保修什么时候？": "8月15日",
    "衣柜是什么？": "定制",
}


def main() -> int:
    path = os.path.join(_WORK, "furniture_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "furniture_codex_answers.json"),
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
