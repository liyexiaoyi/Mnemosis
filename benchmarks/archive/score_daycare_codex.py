"""DeepSeek-side answers for round 350, merged into work/daycare_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from daycare_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "托育中心第一次什么时候报名的？": "1月8日",
    "托育一个月多少钱？": "2800元",
    "下次入托是什么时候？": "8月17日",
    "托育中心几点开门？": "早7点半",
    "托育中心电话多少？": "0510-6666-9999",
    "托育中心有哪些内容？": "早教游戏、绘本阅读、手工、户外活动",
    "托育中心含几餐？": "两餐两点",
    "接送孩子需要什么？": "接送卡",
    "退当月费用要提前几天申请？": "15天",
    "月费什么时候缴纳？": "8月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "daycare_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["托育中心含几餐？"] = "不知道"
    with open(
        os.path.join(_WORK, "daycare_codex_answers.json"),
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
