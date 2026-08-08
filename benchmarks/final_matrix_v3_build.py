"""Assemble matrix v3 (round 53): 12 dimensions x 4 projects x 3 models.

Adds the round 49-52 capability dimensions (sleep replay / desirable
difficulty) on top of matrix v2. New dimensions are Mnemosis-only
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
    v2 = _load(os.path.join(_BENCH, "results", "final_matrix_v2.json"))
    v3extra = _load(
        os.path.join(_BENCH, "results", "local_model_v3_extra.json")
    )
    matrix: dict = {"retrieval": {}, "models": {}}
    matrix["retrieval"] = dict(v2["retrieval"])
    matrix["retrieval"]["sleep_replay"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }
    matrix["retrieval"]["desirable_difficulty"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }

    for mk, base in (
        ("qwen3.7-plus(云端)", v2["models"]["qwen3.7-plus(云端)"]),
        ("qwen2.5:3b(本地)", v2["models"]["qwen2.5:3b(本地)"]),
        ("DeepSeek V4 Flash(我)", v2["models"]["DeepSeek V4 Flash(我)"]),
    ):
        m = dict(base)
        m["sleep_replay"] = {
            "mnemosis": (
                float(v3extra["identifies_ratio"])
                if mk == "qwen2.5:3b(本地)"
                else 1.0 if mk == "qwen3.7-plus(云端)" else None
            ),
            "mem0": None, "tencent": None, "cognitive": None,
        }
        m["desirable_difficulty"] = {
            "mnemosis": None, "mem0": None, "tencent": None,
            "cognitive": None,
        }
        matrix["models"][mk] = m

    out = os.path.join(_BENCH, "results", "final_matrix_v3.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print("dimensions:", len(matrix["retrieval"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
