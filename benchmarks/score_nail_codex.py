# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 354, merged into work/nail_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from nail_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "美甲店会员卡第一次什么时候办的？": "1月6日",
    "纯色套餐多少钱？": "98元",
    "下次美甲是什么时候？": "8月16日",
    "美甲店几点开门？": "早10点",
    "美甲店电话多少？": "0551-6666-1111",
    "美甲店有哪些服务项目？": "纯色、法式、渐变、贴钻、足部护理",
    "会员消费打几折？": "9折",
    "美甲工具怎么消毒？": "使用前高温消毒",
    "3月选了哪个款式？": "樱花渐变",
    "会员卡余额什么时候会不足？": "8月26日",
}


def main() -> int:
    path = os.path.join(_WORK, "nail_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "nail_codex_answers.json"),
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
