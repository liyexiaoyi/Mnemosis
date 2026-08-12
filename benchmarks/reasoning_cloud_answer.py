"""Answer the Chinese reasoning bench for every project with cloud Qwen."""

from __future__ import annotations

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from reasoning_zh_bench import QUESTIONS, score_answer


def _load(path: str) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def main() -> int:
    from cloud_qwen_matrix import cloud_generate

    projects = {
        "mem0_official_top5": _load(
            os.path.join(_BENCH, "results", "reasoning_ctx_mem0.json")
        ),
        "tencent_top5": _load(
            os.path.join(_BENCH, "results", "reasoning_ctx_tencent.json")
        ),
        "cognitive_top5": _load(
            os.path.join(_BENCH, "results", "reasoning_ctx_cognitive.json")
        ),
    }
    report = {}
    for name, data in projects.items():
        hits = 0
        details = []
        by_q = {row["question"]: row for row in data["rows"]}
        for q in QUESTIONS:
            row = by_q.get(q["q"])
            context = "\n".join(f"- {c}" for c in (row or {}).get("context", []))
            prompt = (
                "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。"
                "需要计算时先算清楚再回答。\n\n"
                f"上下文：\n{context}\n\n问题：{q['q']}"
            )
            answer = cloud_generate(prompt, max_tokens=400)
            score = score_answer(answer, q["keys"])
            hits += int(score >= 1.0)
            details.append(
                {
                    "kind": q["kind"],
                    "question": q["q"],
                    "answer": answer,
                    "keys": q["keys"],
                    "score": round(score, 3),
                    "context": (row or {}).get("context", []),
                }
            )
            print(f"  [{name}] {q['q'][:28]:30s} score={score:.2f}", flush=True)
        report[name] = {
            "system": data["system"],
            "retrieval": data.get("retrieval"),
            "n": len(QUESTIONS),
            "accuracy": round(hits / len(QUESTIONS), 3),
            "details": details,
        }
    out = os.path.join(_BENCH, "results", "reasoning_project_compare.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(
        {k: {"system": v["system"], "retrieval": v["retrieval"],
             "accuracy": v["accuracy"]} for k, v in report.items()},
        ensure_ascii=False,
        indent=2,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
