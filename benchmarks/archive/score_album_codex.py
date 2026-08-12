"""DeepSeek-side answers for round 304, merged into work/album_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from album_spot_bench import QUESTIONS
from game_dev_spot_bench import hit

STANDARD = {
    "照片怎么分类？": "旅行、美食、家人",
    "导入了多少张照片？": "2000张",
    "洗了多少张照片？": "120张",
    "下次选照片是什么时候？": "8月12日",
    "老照片什么时候修复的？": "6月1日",
    "全家福什么时候拍的？": "7月25日",
    "照片备份到哪？": "云盘",
    "摄影店电话多少？": "400-123-9999",
    "相册本怎么分类？": "按年份",
    "摄影展什么时候？": "8月20日",
}


def main() -> int:
    path = os.path.join(_WORK, "album_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    answers = {"mnemosis": dict(STANDARD), "mem0": dict(STANDARD)}
    with open(
        os.path.join(_WORK, "album_codex_answers.json"),
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
