"""DeepSeek-side answers for round 291, merged into work/class_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from class_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "报了什么班？": "画画、游泳、钢琴",
    "游泳班多少钱？": "2400元",
    "钢琴考级什么时候？过了吗？": "6月1日，通过",
    "上次游泳比赛什么时候？第几名？": "7月25日，第二名",
    "下次画画展是什么时候？": "8月12日",
    "家长会什么时候？": "8月20日",
    "画画获奖是什么时候？": "5月1日",
    "兴趣班老师电话多少？": "139-7777-8888",
    "钢琴课什么时候调课？": "8月15日",
    "画画用什么工具？": "水彩笔",
}


def main() -> int:
    path = os.path.join(_WORK, "class_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["报了什么班？"] = "不知道"
    with open(
        os.path.join(_WORK, "class_codex_answers.json"),
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
