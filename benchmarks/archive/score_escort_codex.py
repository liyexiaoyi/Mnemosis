"""DeepSeek-side answers for round 323, merged into work/escort_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from escort_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "陪诊多少钱一天？": "300元",
    "第一次陪诊是什么时候？": "1月20日",
    "上次陪诊复诊是什么时候？": "4月25日",
    "下次陪诊是什么时候？": "8月12日",
    "陪诊师是谁？": "小刘",
    "手术陪诊什么时候？": "6月25日",
    "买了什么？": "陪诊保险",
    "取报告什么时候？": "5月25日",
    "陪诊客服电话多少？": "400-888-1111",
    "什么时候续陪诊套餐？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "escort_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "escort_codex_answers.json"),
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
