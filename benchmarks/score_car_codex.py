# -*- coding: utf-8 -*-
"""DeepSeek-side answers for round 272, merged into work/car_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit  # noqa: E402

from car_spot_bench import QUESTIONS  # noqa: E402


ANSWERS = {
    "mnemosis": {
        "车是什么型号？落地多少钱？": "比亚迪海豹，18.6万",
        "上次保养是什么时候？里程多少？": "4月20日，8300km",
        "下次保养是什么时候？": "8月12日三保",
        "上次修车是什么时候？修的什么？": "7月28日，空调",
        "保险一年多少钱？客服电话多少？": "5200元，95510",
        "上次违章是什么？罚多少？": "违停，200元",
        "上次轮胎出问题是什么时候？": "8月5日轮胎气压告警",
        "年检通过了吗？什么时候？": "7月20日通过",
        "车位在哪？月租多少？": "B2-118，400元",
        "多久保养一次？": "5000km或半年",
    },
    "mem0": {
        "车是什么型号？落地多少钱？": "比亚迪海豹，18.6万",
        "上次保养是什么时候？里程多少？": "4月20日，8300km",
        "下次保养是什么时候？": "不知道",
        "上次修车是什么时候？修的什么？": "不知道",
        "保险一年多少钱？客服电话多少？": "5200元，95510",
        "上次违章是什么？罚多少？": "违停，200元",
        "上次轮胎出问题是什么时候？": "8月5日轮胎气压告警",
        "年检通过了吗？什么时候？": "7月20日通过",
        "车位在哪？月租多少？": "B2-118，400元",
        "多久保养一次？": "5000km或半年",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "car_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "car_codex_answers.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(ANSWERS, handle, ensure_ascii=False, indent=2)
    accuracy = {}
    for project, rows in ANSWERS.items():
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
    data["answers_codex"] = ANSWERS
    data["accuracy_codex"] = accuracy
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
