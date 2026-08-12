"""DeepSeek-side answers for round 326, merged into work/security_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from security_spot_bench import QUESTIONS

STANDARD = {
    "买了什么安防设备？": "智能门锁",
    "摄像头装在哪？": "门口",
    "安防什么时候调试的？": "3月15日",
    "下次换摄像头是什么时候？": "8月12日",
    "门锁什么时候换电池的？": "6月5日",
    "云存储什么时候续的？": "5月15日",
    "报警器什么时候测试的？": "7月15日",
    "安防客服电话多少？": "400-555-9999",
    "摄像头密码多少？": "123456",
    "云存储什么时候到期？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "security_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["买了什么安防设备？"] = "不知道"
    with open(
        os.path.join(_WORK, "security_codex_answers.json"),
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
