"""DeepSeek-side answers for round 271, merged into work/live_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from live_spot_bench import QUESTIONS

ANSWERS = {
    "mnemosis": {
        "上次直播是什么时候？卖了多少单？": "6月20日，45单",
        "下次直播是什么时候？": "8月20日新品发布会",
        "小风扇现在多少钱？": "45元",
        "大促直播卖了多少单？销售额多少？": "300单，2.4万",
        "退货率是多少？": "12%",
        "现在主播是谁？什么时候播？": "小美，周日晚播",
        "粉丝什么时候破万的？": "6月1日",
        "上次违规整改是什么时候完成的？": "7月15日",
        "快递合作怎么算？": "全国包邮首重5元",
        "7月佣金多少？": "8600元",
    },
    "mem0": {
        "上次直播是什么时候？卖了多少单？": "不知道",
        "下次直播是什么时候？": "8月20日新品发布会",
        "小风扇现在多少钱？": "45元",
        "大促直播卖了多少单？销售额多少？": "300单，2.4万",
        "退货率是多少？": "12%",
        "现在主播是谁？什么时候播？": "小美，周日晚播",
        "粉丝什么时候破万的？": "6月1日",
        "上次违规整改是什么时候完成的？": "7月15日",
        "快递合作怎么算？": "全国包邮首重5元",
        "7月佣金多少？": "8600元",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "live_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "live_codex_answers.json"),
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
