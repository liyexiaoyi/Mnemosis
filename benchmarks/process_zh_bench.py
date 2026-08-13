"""Chinese process-reasoning benchmark (round 31, chain-of-thought steps).

Six scenarios, each a dated step sequence ("阿丽是怎么准备去京都旅行的？").
The correct context must contain ALL steps in chronological order. Runs the
same scenarios through real projects (Mnemosis recall_steps / plain recall,
mem0, TencentDB Agent Memory, cognitive-memory) and answers with cloud
qwen3.7-plus.

Usage:
    python benchmarks/process_zh_bench.py --project mnemosis_steps
    python benchmarks/process_zh_bench.py --project mnemosis_plain
    codex-runtime python benchmarks/process_zh_bench.py --project mem0
    codex-runtime python benchmarks/process_zh_bench.py --project tencent
    system python benchmarks/process_zh_bench.py --project cognitive
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from contextlib import suppress

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

SCENARIOS = [
    {
        "person": "阿丽",
        "question": "阿丽是怎么准备去京都旅行的？",
        "steps": [
            "阿丽在2026年4月1日订了去京都的机票。",
            "阿丽在2026年4月2日买了相机。",
            "阿丽在2026年4月3日收拾了行李。",
            "阿丽在2026年4月4日去了京都。",
            "阿丽在2026年4月5日回到了家。",
        ],
        "keys": ["机票", "相机", "行李"],
    },
    {
        "person": "小波",
        "question": "小波是怎么准备生日派对的？",
        "steps": [
            "小波在2026年5月1日买了蛋糕。",
            "小波在2026年5月2日订了餐厅。",
            "小波在2026年5月3日买了气球。",
            "小波在2026年5月4日请了朋友来家里。",
        ],
        "keys": ["蛋糕", "餐厅", "气球", "朋友"],
    },
    {
        "person": "琳琳",
        "question": "琳琳是怎么搬家的？",
        "steps": [
            "琳琳在2026年6月1日找了搬家公司。",
            "琳琳在2026年6月2日打包了箱子。",
            "琳琳在2026年6月3日搬到了新家。",
            "琳琳在2026年6月4日收拾了新房间。",
            "琳琳在2026年6月5日请邻居吃饭。",
        ],
        "keys": ["搬家公司", "箱子", "新家", "房间", "邻居"],
    },
    {
        "person": "大壮",
        "question": "大壮是怎么学做菜的？",
        "steps": [
            "大壮在2026年7月1日买了菜谱。",
            "大壮在2026年7月2日买了锅。",
            "大壮在2026年7月3日学会了切菜。",
            "大壮在2026年7月4日学会了炒菜。",
        ],
        "keys": ["菜谱", "锅", "切菜", "炒菜"],
    },
    {
        "person": "强强",
        "question": "强强是怎么开始晨跑的？",
        "steps": [
            "强强在2026年8月1日买了跑鞋。",
            "强强在2026年8月2日定了闹钟。",
            "强强在2026年8月3日跑了第一公里。",
            "强强在2026年8月4日坚持跑了一周。",
        ],
        "keys": ["跑鞋", "闹钟", "第一公里", "一周"],
    },
    {
        "person": "朵朵",
        "question": "朵朵是怎么学会养花的？",
        "steps": [
            "朵朵在2026年9月1日买了花盆。",
            "朵朵在2026年9月2日买了花种子。",
            "朵朵在2026年9月3日学会了浇水。",
            "朵朵在2026年9月4日学会了施肥。",
        ],
        "keys": ["花盆", "种子", "浇水", "施肥"],
    },
]

_SYNONYM_CHECKS = [
    {"question": "琳琳是怎么迁居的？", "scenario_index": 2},
    {"question": "大壮是怎么学习做菜的？", "scenario_index": 3},
    {"question": "阿丽是怎么筹备去京都旅游的？", "scenario_index": 0},
]


def _distractors() -> list[str]:
    out = []
    for s in SCENARIOS:
        out.append(f"{s['person']}喜欢蓝色。")
        out.append(f"{s['person']}最喜欢的食物是饺子。")
    return out


def _memories() -> list[str]:
    out = []
    for s in SCENARIOS:
        out.extend(s["steps"])
    out.extend(_distractors())
    return out


def _order_score(context: list[str], steps: list[str]) -> int:
    indexes = [context.index(step) + 1 for step in steps if step in context]
    if not indexes:
        return 0
    return int(indexes == sorted(indexes))


def _coverage(context: list[str], steps: list[str]) -> int:
    return sum(1 for step in steps if step in context)


def _answer_cloud(question: str, context: list[str]) -> str:
    from cloud_qwen_matrix import cloud_generate

    prompt = (
        "只用下面的记忆上下文回答中文问题；如果上下文里有步骤，请按时间顺序"
        "列出关键步骤，每步一行。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in context)
        + f"\n\n问题：{question}"
    )
    return cloud_generate(prompt, max_tokens=600)


def _mnemosis(use_steps: bool) -> dict:
    from mnemosis import MemoryEngine
    from mnemosis.types import MemoryKind, SourceRecord, SourceType

    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content in _memories():
        cue = re.split(r"[在比喜欢最]", content, maxsplit=1)[0]
        kind = (
            MemoryKind.EPISODIC
            if re.search(r"\d{4}年", content)
            else MemoryKind.SEMANTIC
        )
        engine.remember(
            content,
            kind=kind,
            source=source,
            cues=[cue],
        )
    rows = []
    for s in SCENARIOS:
        results = (
            engine.recall_steps(s["question"], top_k=8)
            if use_steps
            else engine.recall(s["question"], top_k=8, reasoning_pack=True)
        )
        rows.append(
            {
                "question": s["question"],
                "context": [r.item.content for r in results],
            }
        )
    engine.close()
    return {
        "system": "Mnemosis recall_steps" if use_steps else "Mnemosis plain top-8",
        "rows": rows,
    }


def _run_mem0() -> dict:
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
                "collection_name": "mem0_process_bench",
                "path": os.path.join(_BENCH, "..", "..", "work", "mem0db"),
            },
        },
    }
    mem = Memory.from_config(cfg)
    for m in _memories():
        mem.add(m, user_id="u1", infer=False)
    rows = []
    for s in SCENARIOS:
        resp = mem.search(s["question"], filters={"user_id": "u1"}, limit=5)
        rows.append(
            {
                "question": s["question"],
                "context": [r.get("memory", "") for r in resp.get("results", [])],
            }
        )
    return {"system": "mem0 official (mem0ai 2.0.17)", "rows": rows}


def _run_tencent() -> dict:
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
    for i, m in enumerate(_memories()):
        client.add_conversation(
            session_id=f"process-s{i}",
            messages=[{"role": "user", "content": m}],
            user_id="u1",
        )
    deadline = time.time() + 600
    while time.time() < deadline:
        with suppress(Exception):
            with urllib.request.urlopen(
                "http://127.0.0.1:8420/health", timeout=5
            ) as resp:
                h = json.loads(resp.read().decode("utf-8"))
            pw = h["services"]["pipelineWorker"]
            if pw["tasksCompleted"] + pw["tasksFailed"] >= len(_memories()):
                break
        time.sleep(5)
    rows = []
    for s in SCENARIOS:
        hits = client.search_atomic(query=s["question"], limit=5, user_id="u1")
        rows.append(
            {
                "question": s["question"],
                "context": [
                    item.get("content") or item.get("memory") or ""
                    for item in hits.get("items", [])
                ],
            }
        )
    return {"system": "TencentDB Agent Memory (cloud L1)", "rows": rows}


def _run_cognitive() -> dict:
    _USER_SITE = os.path.join(
        os.environ.get("APPDATA", ""), "Python", "Python314", "site-packages"
    )
    if os.path.isdir(_USER_SITE) and _USER_SITE not in sys.path:
        sys.path.insert(0, _USER_SITE)
    from cognitive_memory import SyncCognitiveMemory

    mem = SyncCognitiveMemory(embedder="hash")
    for m in _memories():
        mem.add(m, category="episodic" if re.search(r"\d{4}年", m) else "core")
    rows = []
    for s in SCENARIOS:
        resp = mem.search(s["question"], top_k=5)
        rows.append(
            {
                "question": s["question"],
                "context": [r.memory.content for r in resp.results],
            }
        )
    return {"system": "cognitive-memory 0.5.1 (hash embedder)", "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project",
        choices=[
            "mnemosis_steps", "mnemosis_plain",
            "mem0", "tencent", "cognitive",
        ],
    )
    parser.add_argument("--out", default=None)
    parser.add_argument(
        "--retrieval-only",
        action="store_true",
        help="skip cloud answering (CI smoke)",
    )
    parser.add_argument(
        "--synonym-check",
        action="store_true",
        help="Mnemosis-only: recall_steps with Chinese synonym questions",
    )
    args = parser.parse_args()
    if args.synonym_check:
        from mnemosis import MemoryEngine
        from mnemosis.types import MemoryKind, SourceRecord, SourceType

        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        for content in _memories():
            cue = re.split(r"[在比喜欢最]", content, maxsplit=1)[0]
            kind = (
                MemoryKind.EPISODIC
                if re.search(r"\d{4}年", content)
                else MemoryKind.SEMANTIC
            )
            engine.remember(content, kind=kind, source=source, cues=[cue])
        report = {"n": len(_SYNONYM_CHECKS), "rows": []}
        for check in _SYNONYM_CHECKS:
            s = SCENARIOS[check["scenario_index"]]
            results = engine.recall_steps(check["question"], top_k=8)
            context = [r.item.content for r in results]
            cov = _coverage(context, s["steps"])
            ordered = int(cov == len(s["steps"])) and _order_score(
                context, s["steps"]
            )
            report["rows"].append(
                {
                    "question": check["question"],
                    "coverage": cov,
                    "steps": len(s["steps"]),
                    "ordered": bool(ordered),
                }
            )
            print(
                f"  [synonym] {check['question'][:22]:24s} "
                f"cov={cov}/{len(s['steps'])} order={ordered}",
                flush=True,
            )
        engine.close()
        out = args.out or os.path.join(
            _BENCH, "results", "process_zh_synonym_check.json"
        )
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, indent=2)
        return 0
    if args.project == "mnemosis_steps":
        data = _mnemosis(use_steps=True)
    elif args.project == "mnemosis_plain":
        data = _mnemosis(use_steps=False)
    elif args.project == "mem0":
        data = _run_mem0()
    elif args.project == "tencent":
        data = _run_tencent()
    else:
        data = _run_cognitive()

    by_q = {row["question"]: row for row in data["rows"]}
    stats = {"coverage": 0, "ordered": 0, "n": len(SCENARIOS)}
    details = []
    for s in SCENARIOS:
        context = by_q[s["question"]]["context"]
        cov = _coverage(context, s["steps"])
        ordered = int(cov == len(s["steps"])) and _order_score(
            context, s["steps"]
        )
        stats["coverage"] += cov
        stats["ordered"] += ordered
        answer = ""
        score = int(cov == len(s["steps"]) and ordered)
        if not args.retrieval_only:
            answer = _answer_cloud(s["question"], context)
            score = int(all(k in answer for k in s["keys"]))
        details.append(
            {
                "question": s["question"],
                "steps": s["steps"],
                "keys": s["keys"],
                "coverage": cov,
                "ordered": bool(ordered),
                "answer": answer,
                "score": score,
                "context": context,
            }
        )
        print(
            f"  [{args.project}] {s['question'][:24]:26s} "
            f"cov={cov}/{len(s['steps'])} order={ordered} score={score}",
            flush=True,
        )
    report = {
        "system": data["system"],
        "project": args.project,
        "stats": stats,
        "accuracy": round(
            sum(d["score"] for d in details) / len(details), 3
        ),
        "details": details,
    }
    print(json.dumps(
        {"system": report["system"], "stats": stats,
         "accuracy": report["accuracy"]},
        ensure_ascii=False,
        indent=2,
    ))
    out = args.out or os.path.join(
        _BENCH, "results", f"process_zh_{args.project}.json"
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
