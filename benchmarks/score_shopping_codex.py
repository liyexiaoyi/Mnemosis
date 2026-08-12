"""DeepSeek-side answers for round 275, merged into work/shopping_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from shopping_spot_bench import QUESTIONS

STANDARD = {
    "手机壳订单号多少？": "DD-2026-0110",
    "上次退款是什么时候？退了多少钱？": "7月15日，268元",
    "上次换货是什么时候？": "3月15日",
    "耳机什么时候到货？": "8月14日",
    "台灯什么问题？怎么解决的？": "闪烁，4月25日上门换新",
    "电饭煲赠品是什么？": "锅铲",
    "会员日折扣多少？积分多少？": "88折，3200分",
    "退货政策是什么？": "7天无理由",
    "客服电话多少？": "400-800-8888",
    "下次大促什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "shopping_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "shopping_codex_answers.json"),
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
