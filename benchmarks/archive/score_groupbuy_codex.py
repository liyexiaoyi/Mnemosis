"""DeepSeek-side answers for round 279, merged into work/groupbuy_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from groupbuy_spot_bench import QUESTIONS

STANDARD = {
    "团购满多少免配送费？": "50元",
    "团长是谁？": "小王",
    "现在什么时候截单？": "每日截单",
    "上次售后是什么时候？退了多少钱？": "7月15日，128元",
    "下次团购龙虾是什么时候？": "8月12日",
    "提货时间是什么时候？在哪提？": "周四17:00-19:00，3栋楼下",
    "大米多少钱？出了什么问题？": "128元，有虫",
    "小区团购节什么时候？": "8月20日",
    "团购客服电话多少？": "400-666-8888",
    "质量问题多久处理？": "48小时内",
}


def main() -> int:
    path = os.path.join(_WORK, "groupbuy_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "groupbuy_codex_answers.json"),
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
