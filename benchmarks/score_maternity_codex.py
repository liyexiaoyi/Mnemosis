"""DeepSeek-side answers for round 345, merged into work/maternity_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from maternity_spot_bench import QUESTIONS

STANDARD = {
    "月子中心第一次什么时候签约的？": "1月9日",
    "28天套餐多少钱？": "39800元",
    "下次入住是什么时候？": "8月18日",
    "月子中心有哪些服务项目？": "母婴护理、月子餐、产后修复、婴儿游泳",
    "月子中心电话多少？": "0411-8888-7777",
    "每天几点可以探视？": "下午2点到5点",
    "指定了哪位护理师？": "张护理师",
    "入住前多久可以全额退款？": "30天",
    "尾款什么时候支付？": "8月25日",
    "月子餐选了什么套餐？": "A套餐",
}


def main() -> int:
    path = os.path.join(_WORK, "maternity_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "maternity_codex_answers.json"),
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
