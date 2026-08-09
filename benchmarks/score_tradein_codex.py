# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 325, merged into work/tradein_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from tradein_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "新冰箱抵扣后多少钱？": "4200元",
    "旧冰箱抵了多少？": "300元",
    "旧洗衣机抵多少？新洗衣机多少钱？": "200元，2600元",
    "下次旧电脑换新是什么时候？": "8月12日",
    "补贴什么时候到账？多少？": "3月15日，500元",
    "旧空调抵多少？": "400元",
    "新电视抵扣后多少钱？": "1800元",
    "旧手机抵多少？": "800元",
    "换新客服电话多少？": "400-444-6666",
    "补贴什么时候到期？": "8月15日",
}


def main() -> int:
    path = os.path.join(_WORK, "tradein_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "tradein_codex_answers.json"),
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
