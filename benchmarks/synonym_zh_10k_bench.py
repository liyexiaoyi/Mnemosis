"""Chinese synonym recall at 10k scale (round 32).

Three dated step sequences are stored with their "canonical" words
("准备/旅行", "饭店/礼品", "迁居/宾馆") and the questions use synonym forms
("筹备/旅游", "餐厅/礼物", "酒店"). The steps are buried under ~10k noise
memories. Compares recall_steps with Chinese synonym expansion on vs off.
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

from reasoning_zh_10k_bench import generate_memories

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

SCENARIOS = [
    {
        "question": "阿丽是怎么筹备去京都旅游的？",
        "steps": [
            "阿丽在2026年4月1日准备了旅行用的行李。",
            "阿丽在2026年4月2日准备了旅行用的相机。",
            "阿丽在2026年4月3日准备了旅行用的地图。",
        ],
        "keys": ["行李", "相机", "地图"],
    },
    {
        "question": "小波是怎么筹备生日派对、订餐厅买礼物的？",
        "steps": [
            "小波在2026年5月2日订了饭店。",
            "小波在2026年5月3日买了礼品。",
            "小波在2026年5月4日买了蛋糕。",
        ],
        "keys": ["饭店", "礼品", "蛋糕"],
    },
    {
        "question": "琳琳是怎么迁居和订酒店的？",
        "steps": [
            "琳琳在2026年6月1日联系了搬家服务。",
            "琳琳在2026年6月2日打包了箱子。",
            "琳琳在2026年6月3日入住宾馆。",
        ],
        "keys": ["搬家服务", "箱子", "宾馆"],
    },
]


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    # noise FIRST so insertion-order ties favor noise, not the steps
    for content in generate_memories():
        cue = content.split("最")[0].split("比")[0].split("买")[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    for s in SCENARIOS:
        for step in s["steps"]:
            match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", step)
            iso = (
                f"{match.group(1)}-{int(match.group(2)):02d}-"
                f"{int(match.group(3)):02d}"
                if match
                else "2026-01-01"
            )
            engine.remember(
                step,
                kind=MemoryKind.EPISODIC,
                source=source,
                cues=[iso],
                auto_cues=False,
                importance=0.7,
            )
    return engine


def _coverage(context: list[str], steps: list[str]) -> int:
    return sum(1 for step in steps if step in context)


def _ordered(context: list[str], steps: list[str]) -> bool:
    indexes = [context.index(step) + 1 for step in steps if step in context]
    return bool(indexes and indexes == sorted(indexes) and len(indexes) == len(steps))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "synonym_zh_10k_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    report = {"memories": len(engine.store.all_active()), "rows": []}
    print("memories:", report["memories"], flush=True)
    for s in SCENARIOS:
        row = {"question": s["question"], "on": {}, "off": {}}
        for flag in (True, False):
            results = engine.recall_steps(
                s["question"], top_k=8, zh_synonyms=flag
            )
            context = [r.item.content for r in results]
            row["on" if flag else "off"] = {
                "coverage": _coverage(context, s["steps"]),
                "steps": len(s["steps"]),
                "ordered": _ordered(context, s["steps"]),
                "context": context,
            }
            print(
                f"  [{('on' if flag else 'off')}] {s['question'][:22]:24s} "
                f"cov={row['on' if flag else 'off']['coverage']}/"
                f"{len(s['steps'])} order="
                f"{int(row['on' if flag else 'off']['ordered'])}",
                flush=True,
            )
        report["rows"].append(row)

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        report["llm"] = []
        for flag in (True, False):
            hits = 0
            details = []
            for s, row in zip(SCENARIOS, report["rows"]):
                context = row["on" if flag else "off"]["context"]
                prompt = (
                    "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。"
                    "如果有步骤请按时间顺序列出。\n\n"
                    "上下文：\n" + "\n".join(f"- {c}" for c in context)
                    + f"\n\n问题：{s['question']}"
                )
                answer = cloud_generate(prompt, max_tokens=400)
                score = int(all(k in answer for k in s["keys"]))
                hits += score
                details.append(
                    {
                        "question": s["question"],
                        "answer": answer,
                        "keys": s["keys"],
                        "score": score,
                    }
                )
                print(
                    f"  [llm-{('on' if flag else 'off')}] "
                    f"{s['question'][:22]:24s} score={score}",
                    flush=True,
                )
            report["llm"].append(
                {
                    "condition": "on" if flag else "off",
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
