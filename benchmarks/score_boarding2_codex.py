"""DeepSeek-side answers for round 336, merged into work/boarding2_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from boarding2_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "猫咪第一次寄养是什么时候？": "1月9日",
    "猫咪第一次寄养一天多少钱？": "80元",
    "下次寄养是什么时候？": "8月16日",
    "寄养中心有什么设施？": "独立猫舍、空调、监控",
    "寄养中心电话多少？": "021-5555-9999",
    "节假日预订寄养要提前多久？": "提前一周",
    "寄养需要带什么资料？": "疫苗本和健康检查报告",
    "预订后多久取消可以全额退款？": "24小时内",
    "猫咪疫苗什么时候到期？": "8月20日",
    "寄养什么时候涨价的？": "7月1日",
}


def main() -> int:
    path = os.path.join(_WORK, "boarding2_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["节假日预订寄养要提前多久？"] = "不知道"
    with open(
        os.path.join(_WORK, "boarding2_codex_answers.json"),
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
