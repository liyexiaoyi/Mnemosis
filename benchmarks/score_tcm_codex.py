"""DeepSeek-side answers for round 335, merged into work/tcm_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from tcm_spot_bench import QUESTIONS

STANDARD = {
    "中医馆第一次挂号是什么时候？": "1月7日",
    "第一次开的中药多少钱？": "320元",
    "下次复诊是什么时候？": "8月9日",
    "中医馆每周几坐诊？": "周三、周日上午",
    "中医馆前台电话多少？": "028-7777-3333",
    "中药费医保报销多少？": "70%",
    "三伏贴什么时候贴的？": "7月12日",
    "秋季养生讲座什么时候？": "8月24日",
    "代煎药需要提前多久送药？": "提前一天",
    "会员卡余额什么时候会不足？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "tcm_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "tcm_codex_answers.json"),
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
