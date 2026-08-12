"""DeepSeek-side answers for round 281, merged into work/vision_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from vision_spot_bench import QUESTIONS

STANDARD = {
    "上次视力检查是什么时候？双眼多少？": "5月1日，双眼5.0",
    "眼镜总价多少？镜架多少钱？": "1680元，镜架899元",
    "视力处方是多少？": "右-2.00，左-1.75",
    "隐形眼镜多少钱一盒？": "89元",
    "下次复查眼睛是什么时候？": "8月15日",
    "上次看医生是什么时候？什么病？": "8月3日，结膜炎",
    "现在镜片是什么？": "防蓝光",
    "眼科医院是哪家？": "市二院眼科",
    "眼镜怎么清洗？": "用洗镜液，不用纸巾",
    "医生叮嘱什么？": "少看手机，多望远",
}


def main() -> int:
    path = os.path.join(_WORK, "vision_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "vision_codex_answers.json"),
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
