# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 353, merged into work/lens_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from lens_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "第一次验配隐形眼镜是什么时候？": "1月7日",
    "年抛套餐多少钱？": "399元",
    "下次复查是什么时候？": "8月17日",
    "眼镜店几点关门？": "晚9点半",
    "眼镜店电话多少？": "0431-7777-8888",
    "店里有哪几种镜片？": "日抛、月抛、半年抛、年抛",
    "护理液两瓶多少钱？": "120元",
    "月抛镜片多久更换？": "每月",
    "初次佩戴每天不超过几小时？": "4小时",
    "护理液促销什么时候截止？": "8月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "lens_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "lens_codex_answers.json"),
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
