"""DeepSeek-side answers for round 296, merged into work/plant_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from plant_spot_bench import QUESTIONS

STANDARD = {
    "买了什么多肉？": "桃蛋、熊童子",
    "多肉什么时候换盆的？": "2月1日",
    "多肉化水什么时候抢救的？怎么救？": "3月5日，控水",
    "上次除虫是什么时候？": "6月1日",
    "下次换大盆是什么时候？": "8月12日",
    "多肉多久浇一次水？": "10天一次",
    "用什么肥料？": "缓释肥",
    "绿萝什么时候剪枝扦插的？": "7月15日",
    "植物店电话多少？": "400-111-9999",
    "植物市集什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "plant_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "plant_codex_answers.json"),
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
