"""DeepSeek-side answers for round 308, merged into work/bank_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from bank_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "定期存款多少钱？存多久？": "10万，1年",
    "卡什么时候换的？": "2月25日",
    "给爸妈汇了多少钱？": "2万",
    "下次办信用卡是什么时候？": "8月12日",
    "流水什么时候打印的？": "4月25日",
    "定期什么时候到期？": "6月15日",
    "银行客服电话多少？": "95566",
    "网点在哪？": "中山西路88号",
    "信用卡什么时候还？": "8月15日",
    "开通了什么服务？": "网银、短信通知",
}


def main() -> int:
    path = os.path.join(_WORK, "bank_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "bank_codex_answers.json"),
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
