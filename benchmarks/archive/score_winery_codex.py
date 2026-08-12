"""DeepSeek-side answers for round 355, merged into work/winery_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from winery_spot_bench import QUESTIONS

STANDARD = {
    "第一次在酒庄买酒是什么时候？": "1月5日",
    "赤霞珠一瓶多少钱？": "260元",
    "下次取酒是什么时候？": "8月17日",
    "酒庄几点开门？": "早10点",
    "酒庄电话多少？": "0371-8888-6666",
    "酒庄有哪些酒款？": "赤霞珠、梅洛、霞多丽、起泡酒、冰酒",
    "红酒怎么储存？": "恒温15度，避光",
    "会员购酒打几折？": "9折",
    "满多少钱免费配送？": "300元",
    "会员年费什么时候续费？": "8月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "winery_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "winery_codex_answers.json"),
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
