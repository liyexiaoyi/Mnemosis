"""Assemble matrix v4 (round 58): 14 dimensions x 4 projects x 3 models.

Adds the round 54-57 capability dimensions (testing effect / spacing and
adaptive spacing) on top of matrix v3. New dimensions are Mnemosis-only
mechanisms; third-party projects are marked unsupported (0).
"""

from __future__ import annotations

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)


def _load(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    v3 = _load(os.path.join(_BENCH, "results", "final_matrix_v3.json"))
    matrix: dict = {"retrieval": {}, "models": {}}
    matrix["retrieval"] = dict(v3["retrieval"])
    matrix["retrieval"]["testing_effect"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }
    matrix["retrieval"]["spacing"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }
    for mk in (
        "qwen3.7-plus(云端)",
        "qwen2.5:3b(本地)",
        "DeepSeek V4 Flash(我)",
    ):
        m = dict(v3["models"][mk])
        m["testing_effect"] = {
            "mnemosis": None, "mem0": None, "tencent": None,
            "cognitive": None,
        }
        m["spacing"] = {
            "mnemosis": None, "mem0": None, "tencent": None,
            "cognitive": None,
        }
        matrix["models"][mk] = m
    out = os.path.join(_BENCH, "results", "final_matrix_v4.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print("dimensions:", len(matrix["retrieval"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
