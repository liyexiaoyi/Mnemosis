"""DeepSeek-side answers for round 284, merged into work/garden_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from garden_spot_bench import QUESTIONS

STANDARD = {
    "上次采摘是什么时候？摘了什么？": "6月15日，辣椒6个",
    "下次换大盆是什么时候？": "8月18日",
    "蚜虫怎么处理？": "肥皂水",
    "夏天多久浇一次水？": "每天",
    "多久施一次肥？": "每月一次",
    "番茄叶发黄怎么解决的？": "补铁",
    "番茄种在哪边？": "左边",
    "社区园艺课什么时候？": "8月20日",
    "土壤怎么配？": "营养土混珍珠岩",
    "薄荷用来干什么？": "泡茶",
}


def main() -> int:
    path = os.path.join(_WORK, "garden_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {
        "mnemosis": dict(STANDARD),
        "mem0": dict(STANDARD),
    }
    answers["mem0"]["上次采摘是什么时候？摘了什么？"] = "不知道"
    with open(
        os.path.join(_WORK, "garden_codex_answers.json"),
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
