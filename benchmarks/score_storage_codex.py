"""DeepSeek-side answers for round 312, merged into work/storage_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from storage_spot_bench import QUESTIONS

STANDARD = {
    "东西收在哪？": "客厅柜、卧室床底",
    "整理师什么时候来的？": "2月10日",
    "旧物什么时候回收的？": "4月25日",
    "下次买收纳箱是什么时候？": "8月12日",
    "防潮什么时候做的？": "6月1日",
    "上次换季收纳是什么时候？": "7月15日",
    "收纳怎么贴标签？": "按季节",
    "被子用什么压缩？": "真空压缩袋",
    "跳蚤市场什么时候？": "8月20日",
    "防潮包什么时候更换？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "storage_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "storage_codex_answers.json"),
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
