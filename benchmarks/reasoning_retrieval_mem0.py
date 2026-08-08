"""Retrieval contexts for the Chinese reasoning bench from official mem0."""

from __future__ import annotations

import json
import os
import sys
import time

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _BENCH)

from reasoning_zh_bench import MEMORIES, QUESTIONS  # noqa: E402


def main() -> int:
    from mem0 import Memory

    cfg = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "qwen2.5:3b",
                "ollama_base_url": "http://127.0.0.1:11434",
                "temperature": 0,
                "max_tokens": 200,
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
                "path": os.path.join(
                    _BENCH, "..", "..", "work", "mem0db"
                ),
            },
        },
    }
    mem = Memory.from_config(cfg)
    t0 = time.perf_counter()
    for content in MEMORIES:
        mem.add(content, user_id="u1", infer=False)
    ingest = time.perf_counter() - t0

    rows = []
    coverage = {"n": 0, "premises5": 0}
    t0 = time.perf_counter()
    for q in QUESTIONS:
        resp = mem.search(q["q"], filters={"user_id": "u1"}, limit=5)
        contents = [r.get("memory", "") for r in resp.get("results", [])]
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
        "system": "mem0 official (mem0ai 2.0.17, nomic embed)",
        "retrieval": coverage,
        "ingest_seconds": round(ingest, 1),
        "search_seconds": round(search, 1),
        "rows": rows,
    }
    out = os.path.join(_BENCH, "results", "reasoning_ctx_mem0.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
