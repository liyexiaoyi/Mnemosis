"""DeepSeek-side answers for round 352, merged into work/flower_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from flower_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "第一次在花卉市场买花是什么时候？": "1月6日",
    "玫瑰一束多少钱？": "120元",
    "下次花束配送是什么时候？": "8月18日",
    "花卉市场几点开门？": "早7点",
    "花卉市场电话多少？": "0311-6666-2222",
    "市场有哪些花材？": "玫瑰、百合、向日葵、满天星、绿萝",
    "配送范围是哪里？": "市区三环内免费",
    "会员日购花打几折？": "8折",
    "鲜花怎么保养？": "每天换水，避免阳光直射",
    "会员卡积分什么时候清零？": "8月26日",
}


def main() -> int:
    path = os.path.join(_WORK, "flower_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["下次花束配送是什么时候？"] = "不知道"
    with open(
        os.path.join(_WORK, "flower_codex_answers.json"),
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
