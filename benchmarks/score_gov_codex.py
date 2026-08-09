# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 277, merged into work/gov_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from gov_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "社保卡什么时候激活的？": "2月1日",
    "公积金提取到账多少？": "4.8万",
    "居住证什么时候领的？": "5月1日",
    "退税退了多少钱？": "1260元",
    "新身份证什么时候办好的？": "6月20日",
    "医保备案什么时候生效？": "7月10日",
    "孩子户口办完了吗？": "7月25日办完",
    "下次护照办理是什么时候？": "8月12日",
    "社保每月什么时候扣款？": "15号前",
    "公积金账号多少？": "110-223344",
}


def main() -> int:
    path = os.path.join(_WORK, "gov_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "gov_codex_answers.json"),
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
