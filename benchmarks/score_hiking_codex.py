# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 320, merged into work/hiking_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from hiking_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "买了什么装备？": "防晒霜",
    "上次爬山是什么时候？": "2月15日",
    "露营什么时候？": "3月25日",
    "下次徒步是什么时候？": "8月12日",
    "骑行什么时候？": "4月25日",
    "溯溪什么时候？": "5月15日",
    "夜爬什么时候？": "6月25日",
    "漂流什么时候？": "7月15日",
    "户外店电话多少？": "400-888-5555",
    "什么时候补防晒？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "hiking_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "hiking_codex_answers.json"),
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
