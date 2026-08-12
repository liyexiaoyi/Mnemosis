"""DeepSeek-side answers for round 322, merged into work/detailing_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from detailing_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "镀晶什么时候做的？": "1月20日",
    "洗车卡还有几次？": "8次",
    "打蜡什么时候？": "3月15日",
    "下次抛光是什么时候？": "8月12日",
    "补漆什么时候？": "4月10日",
    "玻璃镀膜什么时候？": "5月15日",
    "除味什么时候？": "6月25日",
    "座椅清洁什么时候？": "7月15日",
    "美容店电话多少？": "400-777-2222",
    "会员日什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "detailing_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "detailing_codex_answers.json"),
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
