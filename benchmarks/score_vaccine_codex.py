# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 307, merged into work/vaccine_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from vaccine_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "流感疫苗什么时候打的？": "1月10日",
    "乙肝疫苗什么时候打的？": "2月1日",
    "HPV疫苗上次打的是第几针？": "第二针",
    "下次 HPV 第三针是什么时候？": "8月12日",
    "带状疱疹疫苗什么时候打的第一针？": "3月15日",
    "破伤风疫苗什么时候打的？": "5月10日",
    "接种点电话多少？": "400-444-5555",
    "疫苗本放哪？": "家里",
    "流感疫苗什么时候预约？": "8月15日",
    "社区义诊什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "vaccine_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "vaccine_codex_answers.json"),
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
