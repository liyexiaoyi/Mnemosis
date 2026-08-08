"""Chinese price-comparison at 10k scale (round 33).

Five comparison questions use synonym/formal words ("昂贵/廉价") while the
stored price memories contain only numbers ("花了2500元") - no 贵/便宜 in
the memory text. The reasoning premise pack must pull both number memories
into the context so the cloud model can compare.
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

from reasoning_zh_10k_bench import generate_memories  # noqa: E402


SCENARIOS = [
    {
        "question": "阿丽买的相机和小波买的手机，哪个更昂贵？",
        "premises": ["阿丽买相机花了2500元。", "小波买手机花了3000元。"],
        "keys": ["小波"],
    },
    {
        "question": "朵朵和小雨买的音箱，哪个更廉价？",
        "premises": ["朵朵买音箱花了200元。", "小雨买音箱花了600元。"],
        "keys": ["朵朵"],
    },
    {
        "question": "阿丽和小波买的笔记本，谁的单价更廉价？",
        "premises": ["阿丽买了3本笔记本花了90元。", "小波买了2本笔记本花了40元。"],
        "keys": ["小波"],
    },
    {
        "question": "强强和琳琳买的洗衣机，哪个更贵？",
        "premises": ["强强买洗衣机花了800元。", "琳琳买洗衣机花了600元。"],
        "keys": ["强强"],
    },
    {
        "question": "大壮和强强买的自行车，哪个更昂贵？",
        "premises": ["大壮买自行车花了4500元。", "强强买自行车花了5200元。"],
        "keys": ["强强"],
    },
]


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    # extra premises not in the canonical list
    for content, person in (
        ("强强买洗衣机花了800元。", "强强"),
        ("琳琳买洗衣机花了600元。", "琳琳"),
        ("大壮买自行车花了4500元。", "大壮"),
        ("强强买自行车花了5200元。", "强强"),
    ):
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[person],
            importance=0.7,
        )
    for content in generate_memories():
        cue = content.split("最")[0].split("比")[0].split("买")[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    return engine


def _coverage(context: list[str], premises: list[str]) -> int:
    return sum(1 for p in premises if p in context)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "compare_zh_10k_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    report = {"memories": len(engine.store.all_active()), "rows": []}
    print("memories:", report["memories"], flush=True)
    for s in SCENARIOS:
        row = {"question": s["question"], "plain": {}, "pack": {}}
        for label, results in (
            ("plain", engine.recall(s["question"], top_k=5, reasoning_pack=False)),
            ("pack", engine.recall_reasoning(s["question"], top_k=8)),
        ):
            context = [r.item.content for r in results]
            row[label] = {
                "coverage": _coverage(context, s["premises"]),
                "context": context,
            }
            print(
                f"  [{label}] {s['question'][:26]:28s} "
                f"cov={row[label]['coverage']}/2",
                flush=True,
            )
        report["rows"].append(row)

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        report["llm"] = []
        for label in ("plain", "pack"):
            hits = 0
            details = []
            for s, row in zip(SCENARIOS, report["rows"]):
                context = row[label]["context"]
                prompt = (
                    "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。"
                    "需要比较价格时先算清楚。\n\n"
                    f"上下文：\n" + "\n".join(f"- {c}" for c in context)
                    + f"\n\n问题：{s['question']}"
                )
                answer = cloud_generate(prompt, max_tokens=200)
                score = int(any(k in answer for k in s["keys"]))
                hits += score
                details.append(
                    {
                        "question": s["question"],
                        "answer": answer,
                        "keys": s["keys"],
                        "score": score,
                    }
                )
                print(f"  [llm-{label}] {s['question'][:24]:26s} score={score}",
                      flush=True)
            report["llm"].append(
                {
                    "condition": label,
                    "accuracy": round(hits / len(SCENARIOS), 3),
                    "details": details,
                }
            )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
