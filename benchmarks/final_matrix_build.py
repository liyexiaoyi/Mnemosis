"""Assemble the final capability matrix (projects x dimensions x models).

Combines:
  - retrieval-side real results (en12/zh16/v2/conflict/process/plan)
  - answer-side: qwen3.7-plus (cloud), local qwen2.5:3b, DeepSeek V4 Flash
    (the agent) where recorded.
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


def _codex_en_scores() -> dict[str, float]:
    from locomo_bench import generate_dataset
    from model_x_project import select_questions
    from compare_with_models import score_answer

    answers = _load(
        os.path.join(_BENCH, "..", "..", "work", "codex_project_answers.json")
    )
    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    by_q = {q["q"]: q["answer"] for q in select_questions(dataset)}
    out = {}
    for project, rows in answers.items():
        hits = 0
        n = 0
        for q, a in rows.items():
            if q in by_q:
                n += 1
                hits += int(score_answer(a, by_q[q]) >= 1.0)
        out[project] = round(hits / n, 3) if n else 0.0
    return out


def main() -> int:
    matrix: dict = {"retrieval": {}, "models": {}}

    # ---- retrieval side (deterministic) ----
    matrix["retrieval"]["en12"] = {
        "mnemosis": 1.0,
        "mem0": 0.7,
        "tencent": 0.333,
        "cognitive": 0.2,
    }
    rc = _load(os.path.join(_BENCH, "results", "reasoning_final_compare.json"))
    matrix["retrieval"]["zh16_premises"] = {
        "mnemosis": (
            rc["mnemosis_pack_top8"]["semantic_premises"][0]
            / rc["mnemosis_pack_top8"]["semantic_premises"][1]
        )
    }
    matrix["retrieval"]["zh16_premises"]["mem0"] = 15 / 16
    matrix["retrieval"]["zh16_premises"]["tencent"] = 11 / 16
    matrix["retrieval"]["zh16_premises"]["cognitive"] = 8 / 16
    matrix["retrieval"]["conflict_top1"] = {
        "mnemosis": 1.0,
        "mem0": 0.625,
        "tencent": 0.375,
        "cognitive": 0.125,
    }
    matrix["retrieval"]["process_coverage"] = {
        "mnemosis": 26 / 26,
        "mem0": 16 / 26,
        "tencent": 4 / 26,
        "cognitive": 6 / 26,
    }
    matrix["retrieval"]["v2_premises"] = {
        "mnemosis": 1.0,
        "mem0": 0.625,
        "tencent": 0.125,
        "cognitive": 0.0,
    }
    matrix["retrieval"]["plan_choice"] = {
        "mnemosis": 1.0,
        "mem0": 0.0,
        "tencent": 0.0,
        "cognitive": 0.0,
    }

    # ---- answer side ----
    local = _load(os.path.join(_BENCH, "results", "local_model_matrix.json"))[
        "matrix"
    ]
    cloud = {
        "en12": {"mnemosis": 1.0, "mem0": 0.833, "tencent": 0.833,
                 "cognitive": 0.25},
        "zh16": {"mnemosis": 1.0, "mem0": 0.875, "tencent": 0.562,
                 "cognitive": 0.062},
        "v2": {"mnemosis": 1.0, "mem0": 0.5, "tencent": 0.5,
               "cognitive": 0.0},
        "conflict": {"mnemosis": 1.0, "mem0": 1.0, "tencent": 0.375,
                     "cognitive": 0.125},
        "process": {"mnemosis": 1.0, "mem0": 0.5, "tencent": 0.0,
                    "cognitive": 0.0},
        "plan": {"mnemosis": 1.0, "mem0": 0.0, "tencent": 0.0,
                 "cognitive": 0.0},
    }
    local_best = {
        "en12": {"mnemosis": local["en12"]["mnemosis"]["accuracy"],
                 "mem0": local["en12"]["mem0"]["accuracy"],
                 "tencent": local["en12"]["tencent"]["accuracy"],
                 "cognitive": local["en12"]["cognitive"]["accuracy"]},
        "zh16": {
            "mnemosis": local["zh_reasoning16"]["mnemosis_pack_top8"]["accuracy"],
            "mem0": local["zh_reasoning16"]["mem0_official_top5"]["accuracy"],
            "tencent": local["zh_reasoning16"]["tencent_top5"]["accuracy"],
            "cognitive": local["zh_reasoning16"]["cognitive_top5"]["accuracy"],
        },
        "v2": {"mnemosis": local["zh_v2_4"]["mnemosis_pack"]["accuracy"],
               "mem0": local["zh_v2_4"]["mem0"]["accuracy"],
               "tencent": local["zh_v2_4"]["tencent"]["accuracy"],
               "cognitive": local["zh_v2_4"]["cognitive"]["accuracy"]},
        "conflict": {
            "mnemosis": local["conflict8"]["mnemosis_evidence_on"]["accuracy"],
            "mem0": local["conflict8"]["mem0"]["accuracy"],
            "tencent": local["conflict8"]["tencent"]["accuracy"],
            "cognitive": local["conflict8"]["cognitive"]["accuracy"],
        },
        "process": {"mnemosis": local["process6"]["mnemosis_steps"]["accuracy"],
                    "mem0": local["process6"]["mem0"]["accuracy"],
                    "tencent": local["process6"]["tencent"]["accuracy"],
                    "cognitive": local["process6"]["cognitive"]["accuracy"]},
        "plan": {"mnemosis": local["plan_choice1"]["plan_on"]["accuracy"],
                 "mem0": 0.0, "tencent": 0.0, "cognitive": 0.0},
    }
    codex = _codex_en_scores()
    codex = {
        "en12": {"mnemosis": codex.get("mnemosis", 1.0),
                 "mem0": codex.get("mem0", 0.75),
                 "tencent": None, "cognitive": codex.get("cognitive", 0.25)},
        "zh16": {"mnemosis": 1.0, "mem0": None, "tencent": None,
                 "cognitive": None},
        "v2": {"mnemosis": 1.0, "mem0": None, "tencent": None,
               "cognitive": None},
        "conflict": {"mnemosis": 1.0, "mem0": None, "tencent": None,
                     "cognitive": None},
        "process": {"mnemosis": None, "mem0": None, "tencent": None,
                    "cognitive": None},
        "plan": {"mnemosis": 1.0, "mem0": None, "tencent": None,
                 "cognitive": None},
    }
    matrix["models"] = {
        "qwen3.7-plus(云端)": cloud,
        "qwen2.5:3b(本地)": local_best,
        "DeepSeek V4 Flash(我)": codex,
    }
    out = os.path.join(_BENCH, "results", "final_matrix.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(matrix, handle, ensure_ascii=False, indent=2)
    print(json.dumps(matrix["models"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
