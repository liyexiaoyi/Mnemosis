"""Reasoning v2 extra questions: synonym/formal words + multi-premise math.

Four new Chinese reasoning questions on top of the round-27 store:
  - "哪个更昂贵 / 哪个更廉价" (synonym compare words)
  - "一共花了多少钱" (multi-premise addition, 2 price memories each)

Runs Mnemosis (plain top-5 vs premise pack) and the real third-party
packages (mem0 / TencentDB Agent Memory / cognitive-memory) on the same 4
questions with cloud qwen3.7-plus answering.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from reasoning_zh_bench import MEMORIES  # noqa: E402


NEW_QUESTIONS = [
    {
        "kind": "compare",
        "q": "阿丽和小波买的相机与手机，哪个更昂贵？",
        "keys": ["小波"],
        "premises": ["阿丽买相机花了2500元。", "小波买手机花了3000元。"],
    },
    {
        "kind": "compare",
        "q": "阿丽和小波买的笔记本，谁的单价更廉价？",
        "keys": ["小波"],
        "premises": ["阿丽买了3本笔记本花了90元。", "小波买了2本笔记本花了40元。"],
    },
    {
        "kind": "math",
        "q": "阿丽买相机和小波买手机，一共花了多少钱？",
        "keys": ["5500"],
        "premises": ["阿丽买相机花了2500元。", "小波买手机花了3000元。"],
    },
    {
        "kind": "math",
        "q": "小雨和强强买笔记本，一共花了多少钱？",
        "keys": ["230"],
        "premises": ["小雨买了5本笔记本花了150元。", "强强买了4本笔记本花了80元。"],
    },
]


def _score(answer: str, keys: list[str]) -> float:
    norm = re.sub(r"[\s，。！？、,.!?：:]", "", answer or "")
    hits = sum(1 for k in keys if k in norm)
    return hits / len(keys) if keys else 0.0


def _answer_cloud(q: str, context: list[str]) -> str:
    from cloud_qwen_matrix import cloud_generate

    prompt = (
        "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。"
        "需要计算时先算清楚再回答。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in context)
        + f"\n\n问题：{q}"
    )
    return cloud_generate(prompt, max_tokens=400)


def _mnemosis(use_pack: bool) -> dict:
    from mnemosis import MemoryEngine
    from mnemosis.types import MemoryKind, SourceRecord, SourceType

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
    rows = []
    for q in NEW_QUESTIONS:
        results = (
            engine.recall_reasoning(q["q"], top_k=8)
            if use_pack
            else engine.recall(q["q"], top_k=5, reasoning_pack=False)
        )
        rows.append(
            {
                "question": q["q"],
                "context": [r.item.content for r in results],
            }
        )
    engine.close()
    return {
        "system": "Mnemosis 推理前提包" if use_pack else "Mnemosis 普通top-5",
        "rows": rows,
    }


def _mem0_search() -> dict:
    from mem0 import Memory

    cfg = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "qwen2.5:3b",
                "ollama_base_url": "http://127.0.0.1:11434",
                "temperature": 0,
                "max_tokens": 100,
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text",
                "ollama_base_url": "http://127.0.0.1:11434",
            },
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "mem0_reasoning_bench",
                "path": os.path.join(_BENCH, "..", "..", "work", "mem0db"),
            },
        },
    }
    mem = Memory.from_config(cfg)
    rows = []
    for q in NEW_QUESTIONS:
        resp = mem.search(q["q"], filters={"user_id": "u1"}, limit=5)
        rows.append(
            {
                "question": q["q"],
                "context": [r.get("memory", "") for r in resp.get("results", [])],
            }
        )
    return {"system": "mem0 official (mem0ai 2.0.17)", "rows": rows}


def _tencent_search() -> dict:
    _SDK = os.path.normpath(
        os.path.join(
            _BENCH, "..", "..", "work", "gh_repos", "TencentDB-Agent-Memory",
            "sdk", "memory-core", "python",
        )
    )
    sys.path.insert(0, _SDK)
    from tencentdb_agent_memory import MemoryClient

    client = MemoryClient(
        endpoint="http://127.0.0.1:8420", api_key="local", service_id="default"
    )
    rows = []
    for q in NEW_QUESTIONS:
        hits = client.search_atomic(query=q["q"], limit=5, user_id="u1")
        rows.append(
            {
                "question": q["q"],
                "context": [
                    item.get("content") or item.get("memory") or ""
                    for item in hits.get("items", [])
                ],
            }
        )
    return {"system": "TencentDB Agent Memory (cloud L1)", "rows": rows}


def _cognitive_search() -> dict:
    _USER_SITE = os.path.join(
        os.environ.get("APPDATA", ""), "Python", "Python314", "site-packages"
    )
    if os.path.isdir(_USER_SITE) and _USER_SITE not in sys.path:
        sys.path.insert(0, _USER_SITE)
    from cognitive_memory import SyncCognitiveMemory

    mem = SyncCognitiveMemory(embedder="hash")
    for m in MEMORIES:
        mem.add(m, category="core")
    rows = []
    for q in NEW_QUESTIONS:
        resp = mem.search(q["q"], top_k=5)
        rows.append(
            {
                "question": q["q"],
                "context": [r.memory.content for r in resp.results],
            }
        )
    return {"system": "cognitive-memory 0.5.1 (hash embedder)", "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        choices=["mnemosis_plain", "mnemosis_pack", "mem0", "tencent", "cognitive"],
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    if args.project == "mnemosis_plain":
        data = _mnemosis(use_pack=False)
    elif args.project == "mnemosis_pack":
        data = _mnemosis(use_pack=True)
    elif args.project == "mem0":
        data = _mem0_search()
    elif args.project == "tencent":
        data = _tencent_search()
    else:
        data = _cognitive_search()

    by_q = {row["question"]: row for row in data["rows"]}
    details = []
    hits = 0
    for q in NEW_QUESTIONS:
        context = by_q[q["q"]]["context"]
        cov = sum(1 for p in q["premises"] if p in context)
        answer = _answer_cloud(q["q"], context)
        score = _score(answer, q["keys"])
        hits += int(score >= 1.0)
        details.append(
            {
                "question": q["q"],
                "premises": q["premises"],
                "keys": q["keys"],
                "coverage": cov,
                "answer": answer,
                "score": round(score, 3),
                "context": context,
            }
        )
        print(
            f"  [{args.project}] {q['q'][:24]:26s} cov={cov}/2 score={score:.2f}",
            flush=True,
        )
    report = {
        "system": data["system"],
        "project": args.project,
        "n": len(NEW_QUESTIONS),
        "coverage": sum(d["coverage"] for d in details),
        "accuracy": round(hits / len(NEW_QUESTIONS), 3),
        "details": details,
    }
    print(json.dumps(
        {"system": report["system"], "coverage": report["coverage"],
         "accuracy": report["accuracy"]},
        ensure_ascii=False,
        indent=2,
    ))
    out = args.out or os.path.join(
        _BENCH, "results", f"reasoning_v2_{args.project}.json"
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
