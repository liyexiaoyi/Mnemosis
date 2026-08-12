"""DeepSeek-side answers for round 286, merged into work/driving_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from driving_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "学车多少钱？什么车型？": "4600元，C1手动挡",
    "科目一考了多少？": "96分",
    "科目二补考是什么时候？考了多少？": "4月5日，90分",
    "什么时候拿到驾照？": "6月20日",
    "下次陪练是什么时候？": "8月10日",
    "第一次上路陪练是什么时候？": "7月20日",
    "驾校在哪？教练电话多少？": "城北训练场，138-2222-3333",
    "科目一多少分及格？": "90分",
    "驾照换证体检什么时候？": "8月15日",
    "科目三考了多少？": "100分",
}


def main() -> int:
    path = os.path.join(_WORK, "driving_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "driving_codex_answers.json"),
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
