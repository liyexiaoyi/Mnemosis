"""DeepSeek-side answers for round 266, merged into work/study_spot.json."""

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from study_spot_bench import QUESTIONS

ANSWERS = {
    "mnemosis": {
        "上次托福考试是什么时候？考了多少分？": "3月20日，104分",
        "下次去银行办信用卡是什么时候？": "8月22日",
        "A 大学的申请结果是什么？": "offer，奖学金60%",
        "上次面试是什么时候？问了什么？": "5月25日，问科研经历",
        "面签要带什么？": "I-20",
        "体检发现缺什么疫苗？": "乙肝疫苗",
        "什么时候开学？新生注册是什么时候？": "9月1日开学，8月30日注册",
        "宿舍什么时候能入住？": "8月28日",
        "机票是哪天的？从哪里飞到哪里？": "8月25日，上海飞洛杉矶",
        "A 大学的申请费是多少？": "90美元",
    },
    "mem0": {
        "上次托福考试是什么时候？考了多少分？": "3月20日，104分",
        "下次去银行办信用卡是什么时候？": "8月22日",
        "A 大学的申请结果是什么？": "不知道",
        "上次面试是什么时候？问了什么？": "5月25日，问科研经历",
        "面签要带什么？": "I-20",
        "体检发现缺什么疫苗？": "乙肝疫苗",
        "什么时候开学？新生注册是什么时候？": "9月1日开学，8月30日注册",
        "宿舍什么时候能入住？": "8月28日",
        "机票是哪天的？从哪里飞到哪里？": "8月25日，上海飞洛杉矶",
        "A 大学的申请费是多少？": "90美元",
    },
}


def main() -> int:
    path = os.path.join(_WORK, "study_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    with open(
        os.path.join(_WORK, "study_codex_answers.json"),
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
