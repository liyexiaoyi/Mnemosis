"""DeepSeek-side answers for round 299, merged into work/account_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from account_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "开了什么安全设置？": "两步验证、绑定手机",
    "会员多少钱？什么时候到期？": "128元，2027年4月15日",
    "下次换绑邮箱是什么时候？": "8月12日",
    "账号申诉什么时候成功的？": "3月10日",
    "账号迁移什么时候完成的？": "6月25日",
    "什么时候提醒存储空间不足？": "5月30日",
    "开通了什么功能？": "家庭共享",
    "客服邮箱多少？": "support@example.com",
    "会员什么时候续费？": "8月15日",
    "版本更新什么时候？": "7月25日",
}


def main() -> int:
    path = os.path.join(_WORK, "account_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "account_codex_answers.json"),
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
