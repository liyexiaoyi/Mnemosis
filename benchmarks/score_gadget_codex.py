# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 276, merged into work/gadget_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from gadget_spot_bench import QUESTIONS  # noqa: E402


STANDARD = {
    "笔记本多少钱？保修多久？": "8599元，2年",
    "上次维修是什么时候？修的什么？": "7月10日，显示器换排线",
    "上次换新是什么时候？": "3月5日键盘售后换新",
    "下次数据迁移是什么时候？": "8月15日",
    "手机电池怎么了？换电池多少钱？": "鼓包，399元",
    "路由器什么问题？怎么解决的？": "信号差，调位置",
    "平板有保修吗？": "AC+一年",
    "路由器密码多少？": "admin888",
    "主力云盘是什么？多大？": "阿里云盘2TB",
    "平板 AC+ 什么时候检查？": "8月20日前",
}


def main() -> int:
    path = os.path.join(_WORK, "gadget_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "gadget_codex_answers.json"),
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
