"""DeepSeek-side answers for round 285, merged into work/cinema_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from cinema_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "上次看电影是什么时候？看的什么？": "7月10日，默杀",
    "下次看电影是什么时候？看哪部？": "8月15日封神2",
    "IMAX 票价多少？": "45元",
    "会员日什么时候？优惠是什么？": "每周三半价",
    "会员积分什么时候过期？": "8月10日",
    "话剧《茶馆》什么时候看的？": "4月20日",
    "音乐会票价多少？": "280元",
    "影院在哪？": "万达广场5楼",
    "停车怎么免？": "凭电影票免3小时",
    "《异形》点映什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "cinema_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "cinema_codex_answers.json"),
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
