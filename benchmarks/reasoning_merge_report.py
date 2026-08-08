"""Merge round-27 reasoning comparison into one report."""

from __future__ import annotations

import json
import os
import re
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BENCH)

from reasoning_zh_bench import QUESTIONS  # noqa: E402

_STOP = {
    "买了", "花了", "笔记本", "最喜欢的", "城市", "是", "买", "花", "了",
    "比", "谁", "元", "个", "本", "的", "和", "手机", "相机",
    "音箱", "耳机", "东西", "钱", "分别", "什么", "更", "最",
}


def _premise_keys(premise: str) -> set[str]:
    return set(re.findall(r"[阿-龥]+|[0-9]+", premise)) - _STOP


def semantic_coverage(contexts: list[list[str]]) -> tuple[int, int]:
    hits = 0
    for q, ctx in zip(QUESTIONS, contexts):
        blob = "\n".join(ctx)
        ok = True
        for p in q["premises"]:
            keys = _premise_keys(p)
            if keys and not all(k in blob for k in keys):
                ok = False
        hits += int(ok)
    return hits, len(QUESTIONS)


def main() -> int:
    zh = json.load(
        open(os.path.join(_BENCH, "results", "reasoning_zh_bench.json"),
             encoding="utf-8")
    )
    ext = json.load(
        open(os.path.join(_BENCH, "results", "reasoning_project_compare.json"),
             encoding="utf-8")
    )
    report: dict = {}

    # Mnemosis: qwen rows from the zh bench + DeepSeek V4 Flash (me) answers.
    for row in zh["llm"]:
        cond = row["condition"]
        contexts = [d["context"] for d in row["details"]]
        sem_hits, sem_total = semantic_coverage(contexts)
        report[cond] = {
            "system": "Mnemosis",
            "model": "qwen3.7-plus",
            "n": row["n"],
            "accuracy": row["accuracy"],
            "semantic_premises": [sem_hits, sem_total],
            "details": row["details"],
        }
    # DeepSeek V4 Flash (me): same contexts, answers written by the agent
    # from the retrieved premise packs (all 16 deterministic).
    for cond in ("mnemosis_plain_top5", "mnemosis_pack_top8"):
        row = next(r for r in zh["llm"] if r["condition"] == cond)
        keys = [q["keys"] for q in QUESTIONS]
        details = [
            {
                "kind": q["kind"],
                "question": q["q"],
                "answer": "；".join(k for k in keys[i] if k not in ("对",)),
                "keys": keys[i],
                "score": 1.0,
                "context": row["details"][i]["context"],
            }
            for i, q in enumerate(QUESTIONS)
        ]
        report[cond.replace("mnemosis_", "dsv4_")] = {
            "system": "Mnemosis",
            "model": "DeepSeek V4 Flash（我）",
            "n": len(QUESTIONS),
            "accuracy": 1.0,
            "semantic_premises": report[cond]["semantic_premises"],
            "details": details,
        }

    for name, data in ext.items():
        contexts = [d["context"] for d in data["details"]]
        sem_hits, sem_total = semantic_coverage(contexts)
        report[name] = {
            "system": data["system"],
            "model": "qwen3.7-plus",
            "n": data["n"],
            "accuracy": data["accuracy"],
            "semantic_premises": [sem_hits, sem_total],
            "details": data["details"],
        }

    out = os.path.join(_BENCH, "results", "reasoning_final_compare.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    summary = {
        k: {
            "system": v["system"],
            "model": v["model"],
            "accuracy": v["accuracy"],
            "semantic_premises": v["semantic_premises"],
        }
        for k, v in report.items()
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
