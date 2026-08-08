"""Evidence-weighted conflict resolution benchmark (round 29).

Eight scenarios where two same-pattern facts disagree (e.g. two different
"favorite color" facts for the same person). The winner has more
confirmations (evidence_count); the loser and distractors have one. The
system should surface the best-evidenced fact first so the LLM answers with
it. Evaluates Mnemosis with evidence weighting on/off, then (optionally)
the same 8 scenarios with qwen3.7-plus answering.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


SCENARIOS = [
    {
        "question": "阿丽最喜欢的颜色是什么？",
        "person": "阿丽",
        "loser": "阿丽最喜欢的颜色是红色。",
        "winner": "阿丽最喜欢的颜色是琥珀色。",
        "winner_evidence": 6,
        "keys": ["琥珀色"],
        "distractors": ["阿丽喜欢蓝色。", "阿丽喜欢绿色。"],
    },
    {
        "question": "小波最喜欢的食物是什么？",
        "person": "小波",
        "loser": "小波最喜欢的食物是拉面。",
        "winner": "小波最喜欢的食物是饺子。",
        "winner_evidence": 5,
        "keys": ["饺子"],
        "distractors": ["小波喜欢面条。", "小波喜欢火锅。"],
    },
    {
        "question": "琳琳最喜欢的城市是什么？",
        "person": "琳琳",
        "loser": "琳琳最喜欢的城市是广州。",
        "winner": "琳琳最喜欢的城市是西安。",
        "winner_evidence": 4,
        "keys": ["西安"],
        "distractors": ["琳琳喜欢南京。", "琳琳喜欢武汉。"],
    },
    {
        "question": "大壮买手机花了多少钱？",
        "person": "大壮",
        "loser": "大壮买手机花了2500元。",
        "winner": "大壮买手机花了3000元。",
        "winner_evidence": 5,
        "keys": ["3000"],
        "distractors": ["大壮买耳机花了200元。", "大壮买手表花了800元。"],
    },
    {
        "question": "强强最喜欢的运动是什么？",
        "person": "强强",
        "loser": "强强最喜欢的运动是跑步。",
        "winner": "强强最喜欢的运动是游泳。",
        "winner_evidence": 6,
        "keys": ["游泳"],
        "distractors": ["强强喜欢踢球。", "强强喜欢爬山。"],
    },
    {
        "question": "朵朵喜欢什么颜色？",
        "person": "朵朵",
        "loser": "朵朵喜欢红色。",
        "winner": "朵朵喜欢蓝色。",
        "winner_evidence": 3,
        "keys": ["蓝色"],
        "distractors": ["朵朵喜欢橙色。", "朵朵喜欢紫色。"],
    },
    {
        "question": "小雨最喜欢的歌手是谁？",
        "person": "小雨",
        "loser": "小雨最喜欢的歌手是林俊杰。",
        "winner": "小雨最喜欢的歌手是周杰伦。",
        "winner_evidence": 5,
        "keys": ["周杰伦"],
        "distractors": ["小雨喜欢听歌。", "小雨喜欢唱歌。"],
    },
    {
        "question": "阿丽比小波高还是矮？",
        "person": "阿丽",
        "loser": "阿丽比小波矮。",
        "winner": "阿丽比小波高。",
        "winner_evidence": 7,
        "keys": ["高"],
        "distractors": ["小波比小王高。", "阿丽比琳琳高。"],
    },
]


def build_engine(use_evidence: bool) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for s in SCENARIOS:
        engine.remember(
            s["loser"],
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[s["person"]],
            evidence_count=1,
        )
        engine.remember(
            s["winner"],
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[s["person"]],
            evidence_count=s["winner_evidence"] if use_evidence else 1,
        )
        for d in s["distractors"]:
            engine.remember(
                d,
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[s["person"]],
                evidence_count=1,
            )
    return engine


def eval_retrieval(engine: MemoryEngine) -> dict:
    stats = {"top1_winner": 0, "winner_in5": 0, "n": len(SCENARIOS)}
    rows = []
    for s in SCENARIOS:
        results = engine.recall(s["question"], top_k=5)
        contents = [r.item.content for r in results]
        rows.append(
            {
                "question": s["question"],
                "top1": contents[0] if contents else "",
                "context": contents,
            }
        )
        stats["top1_winner"] += int(
            bool(contents) and contents[0] == s["winner"]
        )
        stats["winner_in5"] += int(s["winner"] in contents)
    return {"stats": stats, "rows": rows}


def llm_rows(engine_on: MemoryEngine, engine_off: MemoryEngine) -> list[dict]:
    from cloud_qwen_matrix import cloud_generate

    rows = []
    for label, engine in (("evidence_on", engine_on), ("evidence_off", engine_off)):
        hits = 0
        details = []
        for s, row in zip(SCENARIOS, eval_retrieval(engine)["rows"]):
            context = "\n".join(f"- {c}" for c in row["context"])
            prompt = (
                "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。\n\n"
                f"上下文：\n{context}\n\n问题：{s['question']}"
            )
            answer = cloud_generate(prompt, max_tokens=200)
            score = 1.0 if any(k in answer for k in s["keys"]) else 0.0
            hits += int(score >= 1.0)
            details.append(
                {
                    "question": s["question"],
                    "answer": answer,
                    "keys": s["keys"],
                    "score": score,
                    "context": row["context"],
                }
            )
            print(f"  [{label}] {s['question'][:24]:26s} score={score:.2f}",
                  flush=True)
        rows.append(
            {
                "condition": label,
                "n": len(SCENARIOS),
                "accuracy": round(hits / len(SCENARIOS), 3),
                "details": details,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "conflict_evidence_bench.json"),
    )
    args = parser.parse_args()
    on = build_engine(use_evidence=True)
    off = build_engine(use_evidence=False)
    report = {
        "on": eval_retrieval(on),
        "off": eval_retrieval(off),
        "llm": [],
    }
    if args.llm:
        report["llm"] = llm_rows(on, off)
    print(json.dumps(
        {
            "on": report["on"]["stats"],
            "off": report["off"]["stats"],
            "llm": [
                {"condition": r["condition"], "accuracy": r["accuracy"]}
                for r in report["llm"]
            ],
        },
        ensure_ascii=False,
        indent=2,
    ))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    on.close()
    off.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
