"""DeepSeek-side answers for round 314, merged into work/secondhand_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from secondhand_spot_bench import QUESTIONS

STANDARD = {
    "旧手机卖了多少钱？": "1500元",
    "自行车多少钱？有什么问题？": "600元，变速有问题",
    "旧书卖了多少钱？": "80元",
    "下次面交相机是什么时候？": "8月12日",
    "相机现在挂多少？": "2600元",
    "音箱买了以后检查什么？": "音质",
    "二手平台客服电话多少？": "400-111-7777",
    "交易规则是什么？": "面交验货",
    "什么时候确认收货？": "8月15日",
    "二手市集什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "secondhand_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "secondhand_codex_answers.json"),
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
