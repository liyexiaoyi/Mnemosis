"""English 12-question retrieval contexts for the final matrix.

Reuses the real installed packages (mem0 / Tencent / cognitive) to retrieve
the same 12 LoCoMo questions used in the cloud-model matrix, and Mnemosis
recall. Saves contexts so any model (cloud / local / agent) can be scored.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from locomo_bench import generate_dataset  # noqa: E402
from model_x_project import select_questions  # noqa: E402


def _contexts_for(project: str) -> list[dict]:
    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    questions = select_questions(dataset)
    rows = []
    if project == "mnemosis":
        from mnemosis import MemoryEngine
        from mnemosis.types import MemoryKind, SourceRecord, SourceType

        engine = MemoryEngine()
        source = SourceRecord(origin=SourceType.USER)
        for m in dataset["facts"] + dataset["events"]:
            engine.remember(
                m["content"],
                kind=MemoryKind(m["kind"]),
                source=source,
                cues=m.get("cues"),
                importance=0.8 if m["kind"] == "semantic" else 0.5,
            )
        for q in questions:
            results = engine.recall(q["q"], top_k=5)
            rows.append(
                {
                    "question": q["q"],
                    "expected": q["answer"],
                    "context": [r.item.content for r in results],
                }
            )
        engine.close()
        return rows
    if project == "mem0":
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
                    "collection_name": "mem0_bench_42_24",
                    "path": os.path.join(_BENCH, "..", "..", "work", "mem0db"),
                },
            },
        }
        mem = Memory.from_config(cfg)
        for q in questions:
            resp = mem.search(q["q"], filters={"user_id": "u1"}, limit=5)
            rows.append(
                {
                    "question": q["q"],
                    "expected": q["answer"],
                    "context": [r.get("memory", "") for r in resp.get("results", [])],
                }
            )
        return rows
    if project == "tencent":
        _SDK = os.path.normpath(
            os.path.join(
                _BENCH, "..", "..", "work", "gh_repos",
                "TencentDB-Agent-Memory", "sdk", "memory-core", "python",
            )
        )
        sys.path.insert(0, _SDK)
        from tencentdb_agent_memory import MemoryClient

        client = MemoryClient(
            endpoint="http://127.0.0.1:8420", api_key="local",
            service_id="default",
        )
        for q in questions:
            hits = client.search_atomic(query=q["q"], limit=5, user_id="u1")
            rows.append(
                {
                    "question": q["q"],
                    "expected": q["answer"],
                    "context": [
                        item.get("content") or item.get("memory") or ""
                        for item in hits.get("items", [])
                    ],
                }
            )
        return rows
    # cognitive
    _USER_SITE = os.path.join(
        os.environ.get("APPDATA", ""), "Python", "Python314", "site-packages"
    )
    if os.path.isdir(_USER_SITE) and _USER_SITE not in sys.path:
        sys.path.insert(0, _USER_SITE)
    from cognitive_memory import SyncCognitiveMemory
    from locomo_bench import build_engine

    mem = SyncCognitiveMemory(embedder="hash")
    engine = build_engine(dataset)
    for m in dataset["facts"] + dataset["events"]:
        mem.add(
            m["content"],
            category="core" if m["kind"] == "semantic" else "episodic",
        )
    for q in questions:
        resp = mem.search(q["q"], top_k=5)
        rows.append(
            {
                "question": q["q"],
                "expected": q["answer"],
                "context": [r.memory.content for r in resp.results],
            }
        )
    engine.close()
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--project", choices=["mnemosis", "mem0", "tencent", "cognitive"]
    )
    args = parser.parse_args()
    rows = _contexts_for(args.project)
    out = os.path.join(
        _BENCH, "results", f"en12_ctx_{args.project}.json"
    )
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(rows, handle, ensure_ascii=False, indent=2)
    print(args.project, len(rows), "questions saved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
