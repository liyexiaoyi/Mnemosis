"""DeepSeek-side answers for round 309, merged into work/baking_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from baking_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "做过什么甜点？": "马卡龙",
    "烘焙课什么时候上的？": "2月25日",
    "马卡龙第一次自己做是什么时候？结果如何？": "7月1日，失败",
    "下次做月饼是什么时候？": "8月12日",
    "买了什么设备？": "厨师机",
    "蛋糕装饰课什么时候？": "4月25日",
    "烤箱多少度？": "170度",
    "烘焙店电话多少？": "400-222-8888",
    "什么时候买淡奶油？": "8月15日",
    "生日蛋糕什么时候做的？": "5月1日",
}


def main() -> int:
    path = os.path.join(_WORK, "baking_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["做过什么甜点？"] = "不知道"
    with open(
        os.path.join(_WORK, "baking_codex_answers.json"),
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
