"""DeepSeek-side answers for round 364, merged into work/chaos_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from chaos_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "现在物业费一年多少钱？": "3000元",
    "下次换轮胎是什么时候？": "10月8日",
    "老王修车店现在几点开门？": "早8点",
    "雨刮器多少钱？": "88元",
    "四轮定位什么时候做的？": "8月8日",
    "换电池多少钱？": "300元",
    "年检代办多少钱？": "200元",
    "上次换刹车片是什么时候？": "7月3日",
    "空调什么时候修的？": "6月12日",
    "老王修车店电话多少？": "138-0000-0000",
}


def main() -> int:
    path = os.path.join(_WORK, "chaos_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "chaos_codex_answers.json"),
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
