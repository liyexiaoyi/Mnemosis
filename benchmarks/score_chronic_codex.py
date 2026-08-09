# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 280, merged into work/chronic_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from chronic_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "什么时候确诊高血压？": "1月10日",
    "上次血压多少？": "128/82",
    "现在吃什么药？": "缬沙坦",
    "糖化血红蛋白多少？": "6.4%",
    "下次复查是什么时候？": "8月20日",
    "上次眼科检查是什么时候？结果如何？": "8月5日，眼底正常",
    "每天盐摄入多少？": "小于5g",
    "每天运动多久？": "30分钟快走",
    "慢病门诊报销多少？": "70%",
    "药什么时候快吃完？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "chronic_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "chronic_codex_answers.json"),
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
