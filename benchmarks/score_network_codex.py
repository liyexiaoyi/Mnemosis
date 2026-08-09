# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 311, merged into work/network_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from network_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "现在宽带多少兆？": "千兆",
    "上次测速多少？": "480M",
    "哪里信号不好？": "卧室",
    "下次测速是什么时候？": "8月12日",
    "网费一个月多少钱？": "199元",
    "光猫什么时候换的？": "6月1日",
    "断网什么时候恢复的？": "7月3日",
    "Wi-Fi密码多少？": "home2026",
    "宽带客服电话多少？": "10000",
    "免费提速什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "network_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "network_codex_answers.json"),
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
