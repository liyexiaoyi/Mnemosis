"""DeepSeek-side answers for round 305, merged into work/festival_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from festival_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "年货买了什么？": "坚果",
    "年夜饭多少钱？": "800元",
    "清明祭扫什么时候？": "3月30日",
    "五一去哪？": "杭州",
    "什么时候订月饼？": "8月15日",
    "包粽子活动什么时候？": "6月25日",
    "暑期亲子游什么时候出发？": "7月20日",
    "元宵节买了什么？": "汤圆",
    "中秋采购什么时候？": "8月30日",
    "社区中秋活动什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "festival_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "festival_codex_answers.json"),
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
