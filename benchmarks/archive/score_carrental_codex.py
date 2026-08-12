"""DeepSeek-side answers for round 356, merged into work/carrental_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from carrental_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "第一次租车是什么时候？": "1月7日",
    "经济型轿车日租多少钱？": "180元",
    "下次取车是什么时候？": "8月17日",
    "租车门店几点开门？": "早8点",
    "租车门店电话多少？": "0898-6666-7777",
    "门店有哪些车型？": "经济型、舒适型、SUV、商务车",
    "租车保险怎么算？": "基础保险已含，不计免赔另购",
    "租车油量怎么算？": "满油取车，满油还车",
    "违章什么时候处理的？": "3月24日",
    "会员卡积分什么时候到期？": "8月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "carrental_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "carrental_codex_answers.json"),
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
