"""Dump the 12-question retrieval contexts for the three projects."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys

os.environ["MEM0_TELEMETRY"] = "False"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from locomo_bench import generate_dataset
from model_x_project import select_questions

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def main() -> int:
    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    questions = select_questions(dataset)
    out = {}

    # --- Mnemosis ---
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for memory in dataset["facts"] + dataset["events"]:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.8 if memory["kind"] == "semantic" else 0.5,
        )
    ctx = {}
    for q in questions:
        k = 5 if q["kind"] == "temporal" else 3
        results = engine.recall(q["q"], top_k=k)
        if q["kind"] == "temporal":

            def event_date(r) -> str:
                m = re.search(r"\d{4}-\d{2}-\d{2}", r.item.content)
                return m.group(0) if m else ""

            results = sorted(results, key=event_date)
            ctx[q["q"]] = [f"{event_date(r)}: {r.item.content}" for r in results]
        else:
            ctx[q["q"]] = [r.item.content for r in results]
    out["mnemosis"] = ctx

    # --- mem0 (separate chroma dir to avoid clashing with the running matrix)
    from mem0 import Memory

    db_path = os.path.join(_WORK, "mem0db_ctxdump")
    if os.path.isdir(db_path):
        shutil.rmtree(db_path)
    cfg = {
        "llm": {
            "provider": "ollama",
            "config": {
                "model": "qwen2.5:3b",
                "ollama_base_url": "http://127.0.0.1:11434",
                "temperature": 0,
                "max_tokens": 500,
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
                "collection_name": "mem0_ctx_dump",
                "path": db_path,
            },
        },
        "history_db_path": os.path.join(_WORK, "mem0_ctx_history.db"),
    }
    mem = Memory.from_config(cfg)
    for memory in dataset["facts"] + dataset["events"]:
        mem.add(memory["content"], user_id="u1", infer=False)
    ctx = {}
    for q in questions:
        resp = mem.search(q["q"], filters={"user_id": "u1"}, limit=3)
        ctx[q["q"]] = [r.get("memory", "") for r in resp.get("results", [])]
    out["mem0"] = ctx

    # --- cognitive-memory (system python subprocess)
    req_file = os.path.join(_WORK, "cm_ctxdump_request.json")
    res_file = os.path.join(_WORK, "cm_ctxdump_result.json")
    with open(req_file, "w", encoding="utf-8") as handle:
        json.dump({"dataset": dataset, "questions": questions, "top_k": 3},
                  handle, ensure_ascii=False)
    runner = os.path.join(_BENCH, "official_cognitive_memory_contexts.py")
    subprocess.run(
        [r"C:\Python314\python.exe", runner, req_file, res_file],
        check=True,
        capture_output=True,
        text=True,
    )
    with open(res_file, encoding="utf-8") as handle:
        out["cognitive"] = json.load(handle)

    with open(os.path.join(_WORK, "project_contexts.json"), "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print("contexts dumped to work/project_contexts.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
