"""Chinese reasoning benchmark (round 27): math / compare / transitive.

Stores real premises plus same-dimension distractors, then asks reasoning
questions that need ALL premises in context. Evaluates:

  - retrieval: plain top-5 vs reasoning premise pack top-8 (premise hit);
  - LLM answer: qwen3.7-plus (cloud) grounded in each context, scored by
    normalized key tokens.

Usage:
    python benchmarks/reasoning_zh_bench.py            # retrieval only
    python benchmarks/reasoning_zh_bench.py --llm      # + cloud answering
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


MEMORIES = [
    "阿丽比小波高。",
    "小波比小王高。",
    "阿丽买相机花了2500元。",
    "小波买手机花了3000元。",
    "阿丽买了3本笔记本花了90元。",
    "小波买了2本笔记本花了40元。",
    "阿丽最喜欢的城市是成都。",
    "小波最喜欢的城市是杭州。",
    "琳琳比大壮高。",
    "大壮比强强高。",
    "朵朵买音箱花了200元。",
    "小雨买音箱花了600元。",
    "小雨买了5本笔记本花了150元。",
    "强强买了4本笔记本花了80元。",
    "琳琳最喜欢的城市是西安。",
    "大壮最喜欢的城市是北京。",
    "阿丽最喜欢的颜色是琥珀色。",
    "小波最喜欢的食物是饺子。",
    # same-dimension distractors (other people) to bury the premises
    "阿东比阿西高。",
    "阿西比阿北高。",
    "阿南比阿北高。",
    "阿东比阿南高。",
    "小刚比小明高。",
    "小明比小华高。",
    "阿花比阿草高。",
    "阿草比阿树高。",
    "阿东买平板花了4500元。",
    "阿西买电脑花了5200元。",
    "小明买手表花了800元。",
    "小华买耳机花了300元。",
    "阿花买手机花了2000元。",
    "阿树买相机花了1800元。",
    "阿东买了6本笔记本花了120元。",
    "阿西买了4本笔记本花了100元。",
    "小明买了3本笔记本花了45元。",
    "小华买了5本笔记本花了60元。",
    "阿东最喜欢的城市是广州。",
    "阿西最喜欢的城市是深圳。",
    "小明最喜欢的城市是南京。",
    "小华最喜欢的城市是武汉。",
    # same-person distractors (consistent with the real premises)
    "阿丽比琳琳高。",
    "琳琳比小波高。",
    "小波比大壮高。",
    "大壮比小王高。",
    "阿丽买耳机花了200元。",
    "小波买钢笔花了50元。",
    "阿丽买了1本笔记本花了30元。",
    "小波买了4本笔记本花了80元。",
    "阿丽喜欢的食物是拉面。",
    "小波喜欢的颜色是天蓝色。",
]

QUESTIONS = [
    {
        "kind": "transitive",
        "q": "阿丽、小波、小王三个人里谁最高？",
        "keys": ["阿丽"],
        "premises": ["阿丽比小波高。", "小波比小王高。"],
    },
    {
        "kind": "transitive",
        "q": "阿丽、小波、小王三个人里谁最矮？",
        "keys": ["小王"],
        "premises": ["阿丽比小波高。", "小波比小王高。"],
    },
    {
        "kind": "math",
        "q": "阿丽和小波买的笔记本，谁的单价更贵？",
        "keys": ["阿丽"],
        "premises": ["阿丽买了3本笔记本花了90元。", "小波买了2本笔记本花了40元。"],
    },
    {
        "kind": "math",
        "q": "阿丽买的笔记本单价是多少元？",
        "keys": ["30"],
        "premises": ["阿丽买了3本笔记本花了90元。"],
    },
    {
        "kind": "math",
        "q": "阿丽买相机和小波买手机，谁花的钱更多？差多少元？",
        "keys": ["小波", "500"],
        "premises": ["阿丽买相机花了2500元。", "小波买手机花了3000元。"],
    },
    {
        "kind": "math",
        "q": "小波买手机一共花了多少钱？",
        "keys": ["3000"],
        "premises": ["小波买手机花了3000元。"],
    },
    {
        "kind": "compare",
        "q": "阿丽买的相机和小波买的手机，哪个更贵？",
        "keys": ["小波"],
        "premises": ["阿丽买相机花了2500元。", "小波买手机花了3000元。"],
    },
    {
        "kind": "compare",
        "q": "阿丽比小波高，对吗？",
        "keys": ["对"],
        "premises": ["阿丽比小波高。"],
    },
    {
        "kind": "multi",
        "q": "阿丽和小波最喜欢的城市分别是什么？",
        "keys": ["成都", "杭州"],
        "premises": ["阿丽最喜欢的城市是成都。", "小波最喜欢的城市是杭州。"],
    },
    {
        "kind": "transitive",
        "q": "琳琳、大壮、强强三个人里谁最高？",
        "keys": ["琳琳"],
        "premises": ["琳琳比大壮高。", "大壮比强强高。"],
    },
    {
        "kind": "math",
        "q": "小雨和强强买的笔记本，谁的单价更贵？",
        "keys": ["小雨"],
        "premises": ["小雨买了5本笔记本花了150元。", "强强买了4本笔记本花了80元。"],
    },
    {
        "kind": "math",
        "q": "朵朵和小雨买的音箱，谁花的钱更多？差多少元？",
        "keys": ["小雨", "400"],
        "premises": ["朵朵买耳机花了200元。", "小雨买音箱花了600元。"],
    },
    {
        "kind": "multi",
        "q": "琳琳和大壮最喜欢的城市分别是什么？",
        "keys": ["西安", "北京"],
        "premises": ["琳琳最喜欢的城市是西安。", "大壮最喜欢的城市是北京。"],
    },
    {
        "kind": "compare",
        "q": "阿丽和小波谁更高？",
        "keys": ["阿丽"],
        "premises": ["阿丽比小波高。"],
    },
    {
        "kind": "math",
        "q": "阿丽买相机花了多少钱？",
        "keys": ["2500"],
        "premises": ["阿丽买相机花了2500元。"],
    },
    {
        "kind": "fact",
        "q": "阿丽最喜欢的颜色是什么？",
        "keys": ["琥珀色"],
        "premises": ["阿丽最喜欢的颜色是琥珀色。"],
    },
]


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content in MEMORIES:
        cue = re.split(r"[比最喜欢买]", content, maxsplit=1)[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    return engine


def _norm(text: str) -> str:
    return re.sub(r"[\s，。！？、,.!?：:]", "", text)


def score_answer(answer: str, keys: list[str]) -> float:
    norm = _norm(answer or "")
    hits = sum(1 for k in keys if k in norm)
    return hits / len(keys) if keys else 0.0


def eval_retrieval(engine: MemoryEngine) -> dict:
    stats: dict[str, dict] = {}
    for q in QUESTIONS:
        kind = q["kind"]
        stats.setdefault(kind, {"n": 0, "plain5": 0, "pack8": 0})
        stats[kind]["n"] += 1
        plain = {r.item.content for r in engine.recall(q["q"], top_k=5)}
        pack = {r.item.content for r in engine.recall_reasoning(q["q"], top_k=8)}
        stats[kind]["plain5"] += int(
            all(p in plain for p in q["premises"])
        )
        stats[kind]["pack8"] += int(all(p in pack for p in q["premises"]))
    return stats


def llm_rows(engine: MemoryEngine, questions: list[dict]) -> list[dict]:
    from cloud_qwen_matrix import cloud_generate

    rows = []
    for condition, top_k, method in (
        ("mnemosis_plain_top5", 5, "recall"),
        ("mnemosis_pack_top8", 8, "recall_reasoning"),
    ):
        hits = 0
        details = []
        for q in questions:
            results = (
                engine.recall(q["q"], top_k=top_k)
                if method == "recall"
                else engine.recall_reasoning(q["q"], top_k=top_k)
            )
            context = "\n".join(f"- {r.item.content}" for r in results)
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
                    "context": [r.item.content for r in results],
                }
            )
            print(
                f"  [{condition}] {q['q'][:30]:32s} score={score:.2f}",
                flush=True,
            )
        rows.append(
            {
                "condition": condition,
                "n": len(questions),
                "accuracy": round(hits / len(questions), 3),
                "details": details,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "reasoning_zh_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    retrieval = eval_retrieval(engine)
    report = {"retrieval": retrieval, "llm": []}
    if args.llm:
        report["llm"] = llm_rows(engine, QUESTIONS)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
