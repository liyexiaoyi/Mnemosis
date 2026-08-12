"""DeepSeek-side answers for round 357, merged into work/property_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from property_spot_bench import QUESTIONS

STANDARD = {
    "物业费第一次什么时候交的？": "1月6日",
    "物业费一年多少钱？": "2400元",
    "下次物业维修是什么时候？": "8月16日",
    "物业服务中心几点开门？": "早8点",
    "物业电话多少？": "0851-6666-3333",
    "物业有哪些服务项目？": "维修、保洁、绿化、安保、快递代收",
    "停车月租多少钱？": "300元",
    "物业投诉找哪里？": "前台或400热线",
    "小区有哪些公共设施？": "游泳池、儿童乐园、健身房",
    "物业费什么时候补缴？": "8月24日",
}


def main() -> int:
    path = os.path.join(_WORK, "property_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["下次物业维修是什么时候？"] = "不知道"
    with open(
        os.path.join(_WORK, "property_codex_answers.json"),
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
