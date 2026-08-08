"""Analogical plan reuse benchmark (round 35, Gick & Holyoak 1980).

Four stored step sequences (trip, party, moving, plant care). The questions
ask for a plan for a NEW person by referencing an old one ("参考阿丽是怎么
准备的"), which requires analogical schema transfer: retrieve the reference
person's steps in chronological order. Runs Mnemosis recall_steps and the
real third-party packages with cloud qwen3.7-plus answering.

Usage:
    python benchmarks/plan_reuse_zh_bench.py --project mnemosis
    codex-runtime python benchmarks/plan_reuse_zh_bench.py --project mem0
    codex-runtime python benchmarks/plan_reuse_zh_bench.py --project tencent
    system python benchmarks/plan_reuse_zh_bench.py --project cognitive
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

SCENARIOS = [
    {
        "question": "大壮想去京都旅行，参考阿丽是怎么准备的？",
        "steps": [
            "阿丽在2026年4月1日订了去京都的机票。",
            "阿丽在2026年4月2日买了相机。",
            "阿丽在2026年4月3日收拾了行李。",
            "阿丽在2026年4月4日去了京都。",
        ],
        "keys": ["机票", "相机", "行李", "京都"],
    },
    {
        "question": "琳琳想办生日派对，参照小波是怎么准备的？",
        "steps": [
            "小波在2026年5月1日买了蛋糕。",
            "小波在2026年5月2日订了餐厅。",
            "小波在2026年5月3日买了气球。",
            "小波在2026年5月4日请了朋友来家里。",
        ],
        "keys": ["蛋糕", "餐厅", "气球", "朋友"],
    },
    {
        "question": "强强想搬家，模仿琳琳是怎么做的？",
        "steps": [
            "琳琳在2026年6月1日找了搬家公司。",
            "琳琳在2026年6月2日打包了箱子。",
            "琳琳在2026年6月3日搬到了新家。",
            "琳琳在2026年6月4日收拾了新房间。",
        ],
        "keys": ["搬家公司", "箱子", "新家", "房间"],
    },
    {
        "question": "小雨想学养花，按照朵朵的方法该怎么做？",
        "steps": [
            "朵朵在2026年9月1日买了花盆。",
            "朵朵在2026年9月2日买了花种子。",
            "朵朵在2026年9月3日学会了浇水。",
            "朵朵在2026年9月4日学会了施肥。",
        ],
        "keys": ["花盆", "种子", "浇水", "施肥"],
    },
]


def _memories() -> list[str]:
    out = []
    for s in SCENARIOS:
        out.extend(s["steps"])
    out.extend([
        "大壮喜欢蓝色。",
        "琳琳喜欢画画。",
        "强强喜欢跑步。",
        "小雨喜欢唱歌。",
        "大壮最喜欢的食物是饺子。",
        "强强最喜欢的城市是西安。",
    ])
    return out


def _coverage(context: list[str], steps: list[str]) -> int:
    return sum(1 for step in steps if step in context)


def _ordered(context: list[str], steps: list[str]) -> bool:
    indexes = [context.index(s) + 1 for s in steps if s in context]
    return bool(indexes and indexes == sorted(indexes) and len(indexes) == len(steps))


def _answer_cloud(q: str, context: list[str]) -> str:
    from cloud_qwen_matrix import cloud_generate

    prompt = (
        "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。"
        "如果上下文里有参考步骤，请按时间顺序列出关键步骤。\n\n"
        f"上下文：\n" + "\n".join(f"- {c}" for c in context)
        + f"\n\n问题：{q}"
    )
    return cloud_generate(prompt, max_tokens=400)


def _mnemosis() -> dict:
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
    rows = []
    for s in SCENARIOS:
        results = engine.recall_steps(s["question"], top_k=8)
        rows.append(
            {
                "question": s["question"],
                "context": [r.item.content for r in results],
            }
        )
    engine.close()
    return {"system": "Mnemosis recall_steps（类比计划复用）", "rows": rows}


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
                "collection_name": "mem0_plan_reuse_bench",
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
            session_id=f"plan-s{i}",
            messages=[{"role": "user", "content": m}],
            user_id="u1",
        )
    deadline = time.time() + 600
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                "http://127.0.0.1:8420/health", timeout=5
            ) as resp:
                h = json.loads(resp.read().decode("utf-8"))
            pw = h["services"]["pipelineWorker"]
            if pw["tasksCompleted"] + pw["tasksFailed"] >= len(_memories()):
                break
        except Exception:  # noqa: BLE001
            pass
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
        mem.add(
            m,
            category="episodic" if re.search(r"\d{4}年", m) else "core",
        )
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
        choices=["mnemosis", "mem0", "tencent", "cognitive"],
    )
    parser.add_argument("--out", default=None)
    args = parser.parse_args()
    if args.project == "mnemosis":
        data = _mnemosis()
    elif args.project == "mem0":
        data = _run_mem0()
    elif args.project == "tencent":
        data = _run_tencent()
    else:
        data = _run_cognitive()

    by_q = {row["question"]: row for row in data["rows"]}
    details = []
    hits = 0
    for s in SCENARIOS:
        context = by_q[s["question"]]["context"]
        cov = _coverage(context, s["steps"])
        ordered = int(cov == len(s["steps"])) and _ordered(context, s["steps"])
        answer = _answer_cloud(s["question"], context)
        score = int(all(k in answer for k in s["keys"]))
        hits += score
        details.append(
            {
                "question": s["question"],
                "coverage": cov,
                "steps": len(s["steps"]),
                "ordered": bool(ordered),
                "answer": answer,
                "keys": s["keys"],
                "score": score,
                "context": context,
            }
        )
        print(
            f"  [{args.project}] {s['question'][:26]:28s} "
            f"cov={cov}/{len(s['steps'])} order={ordered} score={score}",
            flush=True,
        )
    report = {
        "system": data["system"],
        "project": args.project,
        "n": len(SCENARIOS),
        "coverage": sum(d["coverage"] for d in details),
        "ordered": sum(1 for d in details if d["ordered"]),
        "accuracy": round(hits / len(SCENARIOS), 3),
        "details": details,
    }
    print(json.dumps(
        {"system": report["system"], "coverage": report["coverage"],
         "ordered": report["ordered"], "accuracy": report["accuracy"]},
        ensure_ascii=False,
        indent=2,
    ))
    out = args.out or os.path.join(
        _BENCH, "results", f"plan_reuse_{args.project}.json"
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
