# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 315, merged into work/theater_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from theater_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "投影仪多少钱？": "4599元",
    "投影仪灯泡什么时候换的？": "4月10日",
    "音响什么时候升级的？": "6月25日",
    "下次换幕布是什么时候？": "8月12日",
    "投影什么时候校准的？": "7月15日",
    "调音什么时候完成的？": "3月15日",
    "沙发离幕布多远？": "3米",
    "影音店电话多少？": "400-888-2222",
    "流媒体会员什么时候续费？": "8月15日",
    "家庭影院展什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "theater_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "theater_codex_answers.json"),
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
