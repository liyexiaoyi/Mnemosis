"""DeepSeek-side answers for round 273, merged into work/invest_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from invest_spot_bench import QUESTIONS

ANSWERS = {
    "mnemosis": {
        "现在券商佣金是多少？客服电话多少？": "万1.2，95588",
        "现在定投金额是多少？": "每月4000元",
        "宁德时代成本价多少？": "210元",
        "上次卖出可转债是什么时候？赚了多少？": "4月30日，可转债赚320元",
        "下次券商面签是什么时候？": "8月18日",
        "上次国债逆回购赚了多少？": "96元",
        "什么时候报税？": "8月15日前",
        "个股止损线是多少？": "-15%",
        "宁德时代什么时候发业绩？": "8月12日",
        "资金账号多少？": "6688-2026",
    },
    "mem0": {
        "现在券商佣金是多少？客服电话多少？": "万1.2，95588",
        "现在定投金额是多少？": "每月4000元",
        "宁德时代成本价多少？": "210元",
        "上次卖出可转债是什么时候？赚了多少？": "4月30日，可转债赚320元",
        "下次券商面签是什么时候？": "8月18日",
        "上次国债逆回购赚了多少？": "96元",
        "什么时候报税？": "8月15日前",
        "个股止损线是多少？": "-15%",
        "宁德时代什么时候发业绩？": "8月12日",
        "资金账号多少？": "6688-2026",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "invest_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "invest_codex_answers.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(ANSWERS, handle, ensure_ascii=False, indent=2)
    accuracy = {}
    for project, rows in ANSWERS.items():
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
    data["answers_codex"] = ANSWERS
    data["accuracy_codex"] = accuracy
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
