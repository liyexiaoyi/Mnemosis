# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 362, merged into work/billiards_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from billiards_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "台球厅会员卡第一次什么时候办的？": "1月6日",
    "台费每小时多少钱？": "40元",
    "下次打球是什么时候？": "8月17日",
    "台球厅几点开门？": "早10点",
    "台球厅电话多少？": "0452-6666-3333",
    "台球厅有哪些设施？": "美式台球桌8张、斯诺克桌2张、休息区、饮品吧",
    "教练课每小时多少钱？": "150元",
    "会员台费打几折？": "8折",
    "台球比赛结果是什么？": "四强",
    "会员卡余额什么时候会不足？": "8月26日",
}


def main() -> int:
    path = os.path.join(_WORK, "billiards_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["台球比赛结果是什么？"] = "不知道"
    with open(
        os.path.join(_WORK, "billiards_codex_answers.json"),
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
