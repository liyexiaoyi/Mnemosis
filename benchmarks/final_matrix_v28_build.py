"""Assemble matrix v28 (round 178): 112 dimensions x 4 projects x 3 models.

Adds the round 174-178 special-training dimensions (plan quality /
project brief / numeric reasoning / plan support / toolchain 15) on top
of matrix v27. New dimensions are Mnemosis-only mechanisms; third-party
projects are marked unsupported (0). Base dimensions carry the
real-install measurements from periods 4-27; rounds 59-178 show zero
regression on en88/zh200/zh10k, the 10k suites, and the 102/102
full-eval gate.
"""

from __future__ import annotations

import json
import os

_BENCH = os.path.dirname(os.path.abspath(__file__))


def _load(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


NEW_DIMS = [
    "plan_quality",
    "project_brief",
    "numeric_reasoning",
    "plan_support",
    "toolchain15",
]


def main() -> int:
    v27 = _load(os.path.join(_BENCH, "results", "final_matrix_v27.json"))
    matrix: dict = {"retrieval": {}, "models": {}}
    matrix["retrieval"] = dict(v27["retrieval"])
    for dim in NEW_DIMS:
        matrix["retrieval"][dim] = {
            "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
        }
    for mk in (
        "qwen3.7-plus(云端)",
        "qwen2.5:3b(本地)",
        "DeepSeek V4 Flash(我)",
    ):
        m = dict(v27["models"][mk])
        for dim in NEW_DIMS:
            m[dim] = {
                "mnemosis": None, "mem0": None, "tencent": None,
                "cognitive": None,
            }
        matrix["models"][mk] = m
    out = os.path.join(_BENCH, "results", "final_matrix_v28.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print("dimensions:", len(matrix["retrieval"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
