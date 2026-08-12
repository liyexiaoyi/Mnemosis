"""Conflict-resolution benchmark for real third-party projects (round 29).

Same 8 conflict scenarios as ``conflict_evidence_bench``, but ingested into
the official mem0 / TencentDB Agent Memory / cognitive-memory packages
(they have no evidence weighting): the weaker-evidence rival is inserted
first and the winner second. Retrieves top-5, then answers with cloud
qwen3.7-plus.

Usage:
    codex-runtime python benchmarks/conflict_projects_bench.py --project mem0
    codex-runtime python benchmarks/conflict_projects_bench.py --project tencent
    system python benchmarks/conflict_projects_bench.py --project cognitive
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
from contextlib import suppress

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BENCH)

from conflict_evidence_bench import SCENARIOS


def _memories() -> list[str]:
    out = []
    for s in SCENARIOS:
        out.append(s["loser"])
        out.append(s["winner"])
        out.extend(s["distractors"])
    return out


def _answer_cloud(question: str, context: list[str]) -> str:
    from cloud_qwen_matrix import cloud_generate

    prompt = (
        "只用下面的记忆上下文回答中文问题；上下文里没有答案就回答'unknown'。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in context)
        + f"\n\n问题：{question}"
    )
    return cloud_generate(prompt, max_tokens=200)


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
                "collection_name": "mem0_conflict_bench",
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
        contents = [r.get("memory", "") for r in resp.get("results", [])]
        rows.append({"question": s["question"], "context": contents})
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
            session_id=f"conflict-s{i}",
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
        contents = [
            item.get("content") or item.get("memory") or ""
            for item in hits.get("items", [])
        ]
        rows.append({"question": s["question"], "context": contents})
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
        mem.add(m, category="core")
    rows = []
    for s in SCENARIOS:
        resp = mem.search(s["question"], top_k=5)
        contents = [r.memory.content for r in resp.results]
        rows.append({"question": s["question"], "context": contents})
    return {"system": "cognitive-memory 0.5.1 (hash embedder)", "rows": rows}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", choices=["mem0", "tencent", "cognitive"])
    parser.add_argument(
        "--out",
        default=None,
    )
    args = parser.parse_args()
    if args.project == "mem0":
        data = _run_mem0()
    elif args.project == "tencent":
        data = _run_tencent()
    else:
        data = _run_cognitive()

    stats = {"top1_winner": 0, "winner_in5": 0, "n": len(SCENARIOS)}
    details = []
    for s, row in zip(SCENARIOS, data["rows"]):
        contents = row["context"]
        stats["top1_winner"] += int(
            bool(contents) and contents[0] == s["winner"]
        )
        stats["winner_in5"] += int(s["winner"] in contents)
        answer = _answer_cloud(s["question"], contents)
        details.append(
            {
                "question": s["question"],
                "answer": answer,
                "keys": s["keys"],
                "score": int(any(k in answer for k in s["keys"])),
                "top1": contents[0] if contents else "",
                "context": contents,
            }
        )
        print(
            f"  [{args.project}] {s['question'][:24]:26s} "
            f"score={details[-1]['score']}",
            flush=True,
        )
    report = {
        "system": data["system"],
        "project": args.project,
        "retrieval": stats,
        "accuracy": round(
            sum(d["score"] for d in details) / len(details), 3
        ),
        "details": details,
    }
    print(json.dumps(
        {"system": report["system"], "retrieval": stats,
         "accuracy": report["accuracy"]},
        ensure_ascii=False,
        indent=2,
    ))
    out = args.out or os.path.join(
        _BENCH, "results", f"conflict_projects_{args.project}.json"
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
