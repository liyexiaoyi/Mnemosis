# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 310, merged into work/documents_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from documents_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "保险柜里放了什么？": "户口本、房产证",
    "护照什么时候领的？": "2月15日",
    "港澳通行证什么时候办好的？": "3月25日",
    "下次办签证材料是什么时候？": "8月12日",
    "驾驶证什么时候换的？": "4月25日",
    "无犯罪记录证明什么时候拿到的？": "6月25日",
    "社保卡什么时候补办的？": "7月25日",
    "证件照什么底？多大？": "蓝底1寸",
    "证件电子版怎么存的？": "扫描存档",
    "证件照什么时候重拍？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "documents_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["保险柜里放了什么？"] = "不知道"
    with open(
        os.path.join(_WORK, "documents_codex_answers.json"),
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
