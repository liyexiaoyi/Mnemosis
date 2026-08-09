# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 267, merged into work/fitness_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from fitness_spot_bench import QUESTIONS  # noqa: E402


ANSWERS = {
    "mnemosis": {
        "上次体测是什么时候？体脂率多少？": "3月15日，体脂21%",
        "上次私教课练了什么？": "卧推60kg",
        "下次体测是什么时候？": "7月28日",
        "健身卡什么时候续的？多少钱？": "8月2日，1688元",
        "现在卧推能推多少？": "60kg",
        "每周怎么练？": "周一胸、周三背、周五腿",
        "练后吃什么？": "蛋白粉",
        "上次器械维护是什么时候？": "5月10日",
        "下次拉伸课是什么时候？": "8月18日",
        "私教课用哪个柜子？密码多少？": "2号锁柜，密码2233",
    },
    "mem0": {
        "上次体测是什么时候？体脂率多少？": "3月15日，体脂21%",
        "上次私教课练了什么？": "不知道",
        "下次体测是什么时候？": "7月28日",
        "健身卡什么时候续的？多少钱？": "8月2日，1688元",
        "现在卧推能推多少？": "60kg",
        "每周怎么练？": "周一胸、周三背、周五腿",
        "练后吃什么？": "蛋白粉",
        "上次器械维护是什么时候？": "5月10日",
        "下次拉伸课是什么时候？": "8月18日",
        "私教课用哪个柜子？密码多少？": "2号锁柜，密码2233",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "fitness_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "fitness_codex_answers.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(ANSWERS, handle, ensure_ascii=False, indent=2)
    accuracy = {}
    for project, rows in ANSWERS.items():
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
    data["answers_codex"] = ANSWERS
    data["accuracy_codex"] = accuracy
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
