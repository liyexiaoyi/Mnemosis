# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 293, merged into work/dental_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from dental_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "补牙什么时候做的？花了多少钱？": "1月25日，800元",
    "隐形正畸多少钱？": "2.4万",
    "什么时候开始戴牙套？": "4月15日",
    "下次换牙套是什么时候？": "8月12日",
    "上次复查是什么时候？": "7月15日",
    "智齿什么时候拔的？": "6月25日",
    "牙套磨嘴怎么办？": "买正畸蜡",
    "牙医电话多少？": "139-3333-4444",
    "正畸要注意什么？": "吃完东西要刷牙",
    "什么时候复诊？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "dental_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "dental_codex_answers.json"),
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
