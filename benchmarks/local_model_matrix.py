"""Local model (Ollama qwen2.5:3b) answer matrix across dimensions.

Uses the real saved retrieval contexts from every dimension (English 12,
Chinese reasoning 16, reasoning v2 4, conflict 8, process steps 6, plan
choice 1) and answers them with the local qwen2.5:3b, scoring with each
dimension's own rule. Output: accuracy per (dimension, project/condition).
"""

from __future__ import annotations

import json
import os
import re
import sys
import time

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from compare_with_models import ollama_generate  # noqa: E402

MODEL = "qwen2.5:3b"
URL = "http://127.0.0.1:11434"


def _norm(text: str) -> str:
    return re.sub(r"[\s，。！？、,.!?：:]", "", text or "")


def _keys_score(answer: str, keys: list[str]) -> float:
    norm = _norm(answer)
    hits = sum(1 for k in keys if k in norm)
    return hits / len(keys) if keys else 0.0


def _answer(question: str, context: list[str], zh: bool) -> str:
    if zh:
        prompt = (
            "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。"
            "需要计算时先算清楚再回答。\n\n"
            "上下文：\n" + "\n".join(f"- {c}" for c in context)
            + f"\n\n问题：{question}"
        )
    else:
        prompt = (
            "Answer using ONLY the memory context below. "
            "If the context lacks the answer, answer 'unknown'.\n\n"
            "Context:\n" + "\n".join(f"- {c}" for c in context)
            + f"\n\nQuestion: {question}"
        )
    return ollama_generate(MODEL, prompt, URL, timeout=60)


def _load(path: str) -> list[dict] | dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    t0 = time.perf_counter()
    matrix: dict[str, dict] = {}
    total_calls = 0

    def run_dimension(
        name: str,
        conditions: list[tuple[str, list[dict]]],
        *,
        zh: bool,
    ) -> None:
        nonlocal total_calls
        matrix[name] = {}
        for cond, rows in conditions:
            hits = 0
            details = []
            for row in rows:
                if zh:
                    score = _keys_score(
                        _answer(row["question"], row["context"], True),
                        row["keys"],
                    )
                else:
                    answer = _answer(row["question"], row["context"], False)
                    from compare_with_models import score_answer

                    score = score_answer(answer, row["expected"])
                hits += int(score >= 1.0)
                details.append(round(score, 2))
                total_calls += 1
            matrix[name][cond] = {
                "accuracy": round(hits / len(rows), 3),
                "scores": details,
            }
            print(
                f"[{name}] {cond}: {hits}/{len(rows)} "
                f"({round(time.perf_counter() - t0, 1)}s)",
                flush=True,
            )

    # 1) English 12
    en_conds = []
    for project in ("mnemosis", "mem0", "tencent", "cognitive"):
        rows = _load(
            os.path.join(_BENCH, "results", f"en12_ctx_{project}.json")
        )
        en_conds.append(
            (
                project,
                [{"question": r["question"], "context": r["context"],
                  "expected": r["expected"]} for r in rows],
            )
        )
    run_dimension("en12", en_conds, zh=False)

    # 2) Chinese reasoning 16 (conditions from reasoning_final_compare)
    rc = _load(os.path.join(_BENCH, "results", "reasoning_final_compare.json"))
    zh_conds = []
    for cond in (
        "mnemosis_plain_top5", "mnemosis_pack_top8",
        "mem0_official_top5", "tencent_top5", "cognitive_top5",
    ):
        data = rc[cond]
        zh_conds.append(
            (
                cond,
                [{"question": d["question"], "context": d["context"],
                  "keys": d["keys"]} for d in data["details"]],
            )
        )
    run_dimension("zh_reasoning16", zh_conds, zh=True)

    # 3) reasoning v2 (4)
    v2_conds = []
    for cond in ("mnemosis_plain", "mnemosis_pack", "mem0", "tencent", "cognitive"):
        data = _load(
            os.path.join(_BENCH, "results", f"reasoning_v2_{cond}.json")
        )
        v2_conds.append(
            (
                cond,
                [{"question": d["question"], "context": d["context"],
                  "keys": d["keys"]} for d in data["details"]],
            )
        )
    run_dimension("zh_v2_4", v2_conds, zh=True)

    # 4) conflict (8)
    cb = _load(os.path.join(_BENCH, "results", "conflict_evidence_bench.json"))
    cf_conds = [("mnemosis_evidence_on", cb["on"]["rows"]),
                ("mnemosis_baseline", cb["off"]["rows"])]
    for project in ("mem0", "tencent", "cognitive"):
        data = _load(
            os.path.join(_BENCH, "results", f"conflict_projects_{project}.json")
        )
        cf_conds.append((project, data["details"]))
    conflict_rows = []
    from conflict_evidence_bench import SCENARIOS as _CONFLICT_SCENARIOS

    _cf_keys = {s["question"]: s["keys"] for s in _CONFLICT_SCENARIOS}
    for cond, rows in cf_conds:
        norm = []
        for row in rows:
            norm.append(
                {"question": row["question"], "context": row.get("context", []),
                 "keys": row.get("keys") or _cf_keys.get(row["question"], [])}
            )
        conflict_rows.append((cond, norm))
    run_dimension("conflict8", conflict_rows, zh=True)

    # 5) process steps (6) - score by step keys
    pz_conds = []
    for cond in ("mnemosis_steps", "mnemosis_plain", "mem0", "tencent", "cognitive"):
        data = _load(
            os.path.join(_BENCH, "results", f"process_zh_{cond}.json")
        )
        pz_conds.append(
            (
                cond,
                [{"question": d["question"], "context": d["context"],
                  "keys": d["keys"]} for d in data["details"]],
            )
        )
    run_dimension("process6", pz_conds, zh=True)

    # 6) plan choice (1)
    pc = _load(os.path.join(_BENCH, "results", "plan_choice_bench.json"))
    plan_conds = []
    for cond in ("on", "off"):
        plan_conds.append(
            (
                f"plan_{cond}",
                [{"question": "大壮想去京都旅行，参考阿丽和小波谁的计划更好？",
                  "context": pc[cond]["plan"], "keys": ["小波"]}],
            )
        )
    run_dimension("plan_choice1", plan_conds, zh=True)

    report = {
        "model": MODEL,
        "seconds": round(time.perf_counter() - t0, 1),
        "total_calls": total_calls,
        "matrix": matrix,
    }
    out = os.path.join(_BENCH, "results", "local_model_matrix.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(
        {k: {c: v["accuracy"] for c, v in m.items()}
         for k, m in matrix.items()},
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
