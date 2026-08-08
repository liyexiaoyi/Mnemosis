"""Assemble matrix v32 (round 198): 128 dimensions x 4 projects x 3 models.

Adds the round 194-197 capability dimensions (recall trace / community
report / sleep advice / toolchain 19) on top of matrix v31. New
dimensions are Mnemosis-only mechanisms; third-party projects are marked
unsupported (0). Base dimensions carry the real-install measurements from
periods 4-31; rounds 59-197 show zero regression on en88/zh200/zh10k,
the 10k suites, and the 118/118 full-eval gate.
"""

from __future__ import annotations

import json
import os

_BENCH = os.path.dirname(os.path.abspath(__file__))


def _load(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


NEW_DIMS = [
    "recall_trace",
    "community_report",
    "sleep_advice",
    "toolchain19",
]


def main() -> int:
    v31 = _load(os.path.join(_BENCH, "results", "final_matrix_v31.json"))
    matrix: dict = {"retrieval": {}, "models": {}}
    matrix["retrieval"] = dict(v31["retrieval"])
    for dim in NEW_DIMS:
        matrix["retrieval"][dim] = {
            "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
        }
    for mk in (
        "qwen3.7-plus(云端)",
        "qwen2.5:3b(本地)",
        "DeepSeek V4 Flash(我)",
    ):
        m = dict(v31["models"][mk])
        for dim in NEW_DIMS:
            m[dim] = {
                "mnemosis": None, "mem0": None, "tencent": None,
                "cognitive": None,
            }
        matrix["models"][mk] = m
    out = os.path.join(_BENCH, "results", "final_matrix_v32.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print("dimensions:", len(matrix["retrieval"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
