"""Chinese reasoning bench contexts from official TencentDB Agent Memory."""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.request

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_SDK = os.path.normpath(
    os.path.join(
        _BENCH, "..", "..", "work", "gh_repos", "TencentDB-Agent-Memory",
        "sdk", "memory-core", "python",
    )
)
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)
sys.path.insert(0, _SDK)

from reasoning_zh_bench import MEMORIES, QUESTIONS
from tencentdb_agent_memory import MemoryClient

ENDPOINT = "http://127.0.0.1:8420"


def _health() -> dict:
    with urllib.request.urlopen(ENDPOINT + "/health", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    client = MemoryClient(endpoint=ENDPOINT, api_key="local", service_id="default")
    t0 = time.perf_counter()
    for i, content in enumerate(MEMORIES):
        client.add_conversation(
            session_id=f"reason-s{i}",
            messages=[{"role": "user", "content": content}],
            user_id="u1",
        )
    ingest = time.perf_counter() - t0

    deadline = time.time() + 600
    while time.time() < deadline:
        h = _health()
        pw = h["services"]["pipelineWorker"]
        if pw["tasksCompleted"] + pw["tasksFailed"] >= len(MEMORIES):
            break
        time.sleep(5)
    h = _health()
    print("pipeline:", h["services"]["pipelineWorker"], flush=True)

    rows = []
    coverage = {"n": 0, "premises5": 0}
    t0 = time.perf_counter()
    for q in QUESTIONS:
        hits = client.search_atomic(query=q["q"], limit=5, user_id="u1")
        contents = [
            item.get("content") or item.get("memory") or ""
            for item in hits.get("items", [])
        ]
        rows.append(
            {
                "kind": q["kind"],
                "question": q["q"],
                "context": contents,
            }
        )
        coverage["n"] += 1
        coverage["premises5"] += int(
            all(p in contents for p in q["premises"])
        )
    search = time.perf_counter() - t0
    report = {
        "system": "TencentDB Agent Memory (local service, cloud L1)",
        "retrieval": coverage,
        "ingest_seconds": round(ingest, 1),
        "search_seconds": round(search, 1),
        "rows": rows,
    }
    out = os.path.join(_BENCH, "results", "reasoning_ctx_tencent.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
