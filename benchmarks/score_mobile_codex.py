"""DeepSeek-side answers for round 288, merged into work/mobile_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from mobile_spot_bench import QUESTIONS

STANDARD = {
    "现在什么套餐？多少钱？": "5G套餐，129元/月",
    "话费什么时候出账？": "每月5日",
    "流量超了怎么办？": "买10元加油包",
    "5G信号问题怎么解决的？": "换路由器",
    "下次改套餐是什么时候？": "8月10日",
    "副卡给谁办的？": "家人",
    "充 200 送多少？": "送20",
    "客服电话多少？服务密码呢？": "10086，223344",
    "话费什么时候不足？": "8月15日",
    "5G升级活动什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "mobile_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "mobile_codex_answers.json"),
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
