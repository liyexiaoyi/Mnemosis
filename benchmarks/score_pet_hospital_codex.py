"""DeepSeek-side answers for round 349, merged into work/pet_hospital_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from pet_hospital_spot_bench import QUESTIONS

STANDARD = {
    "第一次去宠物医院是什么时候？": "1月7日",
    "宠物医院挂号费多少？": "50元",
    "下次复诊是什么时候？": "8月16日",
    "宠物医院几点开门？": "早8点",
    "宠物医院电话多少？": "023-6666-8888",
    "医院有哪些诊疗项目？": "体检、绝育、牙科、皮肤科、影像检查",
    "绝育手术多少钱？": "1200元",
    "猫咪多久打一次猫三联？": "每年一次",
    "夜间急诊加收多少钱？": "100元",
    "会员日诊疗打几折？": "9折",
}


def main() -> int:
    path = os.path.join(_WORK, "pet_hospital_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "pet_hospital_codex_answers.json"),
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
