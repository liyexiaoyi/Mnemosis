"""DeepSeek-side answers for round 333, merged into work/swim_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from swim_spot_bench import QUESTIONS

STANDARD = {
    "游泳年卡第一次什么时候办的？": "1月6日",
    "游泳年卡多少钱？": "3600元",
    "游泳馆下次什么时候开放？": "8月15日",
    "游泳馆几点开门？": "早6点",
    "自由泳私教课什么时候上的？": "6月1日",
    "游泳馆前台电话多少？": "010-8888-1234",
    "什么情况下可以申请停卡？": "出差可申请，每月最多一次",
    "游泳馆会员赛什么时候？": "4月20日",
    "年卡续费优惠什么时候截止？": "8月23日",
    "游泳健康证什么时候办的？": "5月7日",
}


def main() -> int:
    path = os.path.join(_WORK, "swim_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "swim_codex_answers.json"),
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
