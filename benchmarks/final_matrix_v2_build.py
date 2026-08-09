"""Assemble matrix v2 (round 48): 10 dimensions x 4 projects x 3 models.

Covers the original 6 answer dimensions plus the round 42-46 capability
dimensions (plan effort / replan / prediction / unexpected-event 10k),
which are Mnemosis-only mechanisms (third-party projects do not support
them; marked 0/unsupported).
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
    v1 = _load(os.path.join(_BENCH, "results", "final_matrix.json"))
    local = _load(os.path.join(_BENCH, "results", "local_model_matrix.json"))[
        "matrix"
    ]
    v2extra = _load(
        os.path.join(_BENCH, "results", "local_model_v2_extra.json")
    )
    matrix: dict = {"retrieval": {}, "models": {}}

    # ---- retrieval (10 dimensions) ----
    matrix["retrieval"] = dict(v1["retrieval"])
    matrix["retrieval"]["plan_effort"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }
    matrix["retrieval"]["replan"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }
    matrix["retrieval"]["prediction"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }
    matrix["retrieval"]["unexpected_10k"] = {
        "mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0,
    }

    # ---- answer side: reuse v1 for 6 dimensions, add new dimensions ----
    cloud = dict(v1["models"]["qwen3.7-plus(云端)"])
    cloud["plan_effort"] = {
        "mnemosis": None, "mem0": None, "tencent": None, "cognitive": None,
    }
    cloud["replan"] = {
        "mnemosis": 1.0, "mem0": None, "tencent": None, "cognitive": None,
    }
    cloud["prediction"] = {
        "mnemosis": 1.0, "mem0": None, "tencent": None, "cognitive": None,
    }
    cloud["unexpected_10k"] = {
        "mnemosis": None, "mem0": None, "tencent": None, "cognitive": None,
    }

    local_best = dict(v1["models"]["qwen2.5:3b(本地)"])
    local_best["plan_effort"] = {
        "mnemosis": None, "mem0": None, "tencent": None, "cognitive": None,
    }
    local_best["replan"] = {
        "mnemosis": float(v2extra["replan"]["avoids_ali_flight"]),
        "mem0": None, "tencent": None, "cognitive": None,
    }
    local_best["prediction"] = {
        "mnemosis": float(v2extra["prediction"]["identifies_flight"]),
        "mem0": None, "tencent": None, "cognitive": None,
    }
    local_best["unexpected_10k"] = {
        "mnemosis": None, "mem0": None, "tencent": None, "cognitive": None,
    }

    codex = dict(v1["models"]["DeepSeek V4 Flash(我)"])
    codex["plan_effort"] = {
        "mnemosis": None, "mem0": None, "tencent": None, "cognitive": None,
    }
    codex["replan"] = {
        "mnemosis": 1.0, "mem0": None, "tencent": None, "cognitive": None,
    }
    codex["prediction"] = {
        "mnemosis": 1.0, "mem0": None, "tencent": None, "cognitive": None,
    }
    codex["unexpected_10k"] = {
        "mnemosis": None, "mem0": None, "tencent": None, "cognitive": None,
    }

    matrix["models"] = {
        "qwen3.7-plus(云端)": cloud,
        "qwen2.5:3b(本地)": local_best,
        "DeepSeek V4 Flash(我)": codex,
    }
    out = os.path.join(_BENCH, "results", "final_matrix_v2.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print("dimensions:", len(matrix["retrieval"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
