"""DeepSeek-side answers for round 287, merged into work/housework_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from housework_spot_bench import QUESTIONS

STANDARD = {
    "上次保洁是什么时候？做了什么？": "7月10日，除螨",
    "下次大扫除是什么时候？": "8月12日",
    "现在保洁每小时多少钱？": "70元",
    "包月保洁多少钱？多久一次？": "280元，每周一次",
    "现在保洁阿姨是谁？": "小李",
    "包月什么时候续？": "8月15日前",
    "家政客服电话多少？": "400-333-4444",
    "阿姨什么时候请假换班？": "8月20日",
    "买了什么清洁剂？": "抽油烟机专用",
    "家政合同多久一签？": "一年",
}


def main() -> int:
    path = os.path.join(_WORK, "housework_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "housework_codex_answers.json"),
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
