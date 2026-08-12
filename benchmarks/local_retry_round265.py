"""Retry the one local-model miss 3x per model/project (round 265).

The 求职时间线 question was missed by both local models on both projects
even though the 5月6日 record ranked first in every context; this rerun
checks whether the miss is stable or single-draw noise.
"""

from __future__ import annotations

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)

from game_dev_spot_bench import hit
from job_spot_bench import QUESTIONS
from local_retest_round265 import MODELS, _generate, _prompt

QUESTION = "上次面试是哪一天？面了什么内容？"


def main() -> int:
    path = os.path.join(_WORK, "job_spot.json")
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    q = next(question for question in QUESTIONS if question["q"] == QUESTION)
    out = {}
    for model in MODELS:
        out[model] = {}
        for project in ("mnemosis", "mem0"):
            rows = data["contexts"][project][QUESTION]
            trials = []
            for trial in range(3):
                answer = _generate(model, _prompt(rows, QUESTION))
                ok = hit([answer], q)
                trials.append({"trial": trial + 1, "ok": ok, "answer": answer})
                print(
                    f"[{model}][{project}] trial {trial + 1}: "
                    f"hit={ok}",
                    flush=True,
                )
            out[model][project] = trials
    with open(
        os.path.join(_WORK, "job_local_retry.json"),
        "w",
        encoding="utf-8",
    ) as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
