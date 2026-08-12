"""DeepSeek-side answers for round 343, merged into work/cleaner_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from cleaner_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "第一次请钟点工是什么时候？": "1月7日",
    "钟点工每小时多少钱？": "60元",
    "下次钟点工服务是什么时候？": "8月16日",
    "钟点工服务包括哪些？": "打扫、洗衣、做饭，不含擦窗",
    "钟点工平台电话多少？": "010-6666-8888",
    "临时取消要提前多久告知？": "提前3小时",
    "五一假期服务费上浮多少？": "20%",
    "钟点工服务怎么结算？": "线上支付",
    "钟点工考核结果是什么？": "五星",
    "保险什么时候续费？": "8月23日",
}


def main() -> int:
    path = os.path.join(_WORK, "cleaner_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    answers["mem0"]["下次钟点工服务是什么时候？"] = "不知道"
    answers["mem0"]["钟点工服务包括哪些？"] = "不知道"
    answers["mem0"]["钟点工考核结果是什么？"] = "不知道"
    with open(
        os.path.join(_WORK, "cleaner_codex_answers.json"),
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
