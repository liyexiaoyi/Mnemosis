"""DeepSeek-side answers for round 269, merged into work/baby_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from baby_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

ANSWERS = {
    "mnemosis": {
        "小宝出生时多重？": "3.4kg",
        "上次体检是什么时候？体重多少？": "6月15日，8.1kg",
        "上次打疫苗是什么时候？打的什么？": "6月25日，乙肝第三针",
        "下次儿科复诊是什么时候？": "8月10日",
        "现在辅食加了什么？": "米粉、南瓜泥、鸡蛋黄",
        "幼儿园什么时候入学？材料什么时候交？": "9月1日入学，8月20日交材料",
        "婴儿保险多少钱一年？客服电话多少？": "3200元，400-123-4567",
        "小宝上次发烧什么时候退的？": "7月7日",
        "小宝晚上几点睡？": "9点",
        "一岁前不能吃什么？": "蜂蜜",
    },
    "mem0": {
        "小宝出生时多重？": "3.4kg",
        "上次体检是什么时候？体重多少？": "6月15日，8.1kg",
        "上次打疫苗是什么时候？打的什么？": "6月25日，乙肝第三针",
        "下次儿科复诊是什么时候？": "8月10日",
        "现在辅食加了什么？": "米粉、南瓜泥、鸡蛋黄",
        "幼儿园什么时候入学？材料什么时候交？": "9月1日入学，8月20日交材料",
        "婴儿保险多少钱一年？客服电话多少？": "3200元，400-123-4567",
        "小宝上次发烧什么时候退的？": "7月7日",
        "小宝晚上几点睡？": "9点",
        "一岁前不能吃什么？": "蜂蜜",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "baby_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "baby_codex_answers.json"),
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
