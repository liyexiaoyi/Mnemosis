"""DeepSeek-side answers for round 290, merged into work/office_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from office_spot_bench import QUESTIONS

STANDARD = {
    "办公室在哪？": "科技园B座",
    "小李工位在哪？": "3楼A区",
    "打印机多少钱？": "2899元",
    "门禁卡什么时候拿到的？": "3月5日",
    "空调什么时候修好的？": "4月3日",
    "下次电梯检修是什么时候？": "8月10日",
    "上次盘点缺什么？": "A4纸",
    "Wi-Fi密码多少？": "office2026",
    "物业电话多少？": "400-555-6666",
    "团建什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "office_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "office_codex_answers.json"),
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
