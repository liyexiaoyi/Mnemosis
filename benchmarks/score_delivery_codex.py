"""DeepSeek-side answers for round 324, merged into work/delivery_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from delivery_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "会员多少钱一个月？": "15元",
    "会员红包什么时候第一次用？": "1月20日",
    "满多少减多少？": "满30减8",
    "下次会员日是什么时候？": "8月12日",
    "退款什么时候到账？": "4月10日",
    "免配送什么时候？": "5月15日",
    "会员什么时候续的？": "6月20日",
    "外卖客服电话多少？": "400-333-8888",
    "满多少免配送？": "满20",
    "会员什么时候续费？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "delivery_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "delivery_codex_answers.json"),
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
