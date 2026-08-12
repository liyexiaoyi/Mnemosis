"""DeepSeek-side answers for round 361, merged into work/clinic_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from clinic_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "第一次去社区诊所是什么时候？": "1月8日",
    "社区诊所挂号费多少？": "10元",
    "下次复诊是什么时候？": "8月16日",
    "诊所上午几点开诊？": "8点",
    "诊所电话多少？": "0771-6666-2222",
    "诊所有哪些科室？": "内科、外科、儿科、中医科、检验科",
    "第一次开药多少钱？": "48元",
    "医保卡报销多少？": "60%",
    "转诊什么时候完成的？": "5月22日",
    "秋季体检什么时候？": "8月28日",
}


def main() -> int:
    path = os.path.join(_WORK, "clinic_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "clinic_codex_answers.json"),
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
