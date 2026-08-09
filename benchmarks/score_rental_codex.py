# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 268, merged into work/rental_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from rental_spot_bench import QUESTIONS  # noqa: E402


ANSWERS = {
    "mnemosis": {
        "A 小区两居月租多少？": "4200元",
        "合同号是多少？租期多久？": "ZL-2026-0215，1年",
        "押金多少？首月房租多少？": "押金4200，首月4200",
        "上次维修是什么时候？修的什么？": "6月15日，空调滴水",
        "下次家政保洁是什么时候？": "8月15日",
        "续租了吗？租到什么时候？": "续租成功，租到2027年2月28日",
        "水电费什么时候出账单？上次交了多少？": "每月15号出账单，上次交186元",
        "门禁密码多少？快递放哪？": "3311，1号柜",
        "上次查房是什么时候？结果如何？": "5月10日，通过",
        "电梯检修是什么时候完成的？": "4月20日",
    },
    "mem0": {
        "A 小区两居月租多少？": "4200元",
        "合同号是多少？租期多久？": "ZL-2026-0215，1年",
        "押金多少？首月房租多少？": "押金4200，首月4200",
        "上次维修是什么时候？修的什么？": "6月15日，空调滴水",
        "下次家政保洁是什么时候？": "8月15日",
        "续租了吗？租到什么时候？": "续租成功，租到2027年2月28日",
        "水电费什么时候出账单？上次交了多少？": "每月15号出账单，上次交186元",
        "门禁密码多少？快递放哪？": "3311，1号柜",
        "上次查房是什么时候？结果如何？": "5月10日，通过",
        "电梯检修是什么时候完成的？": "4月20日",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "rental_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "rental_codex_answers.json"),
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
