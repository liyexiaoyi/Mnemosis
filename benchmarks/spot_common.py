"""Shared runner for Mnemosis-vs-mem0 spot checks (mem0 official only)."""

from __future__ import annotations

import json
import os
import shutil

_SRC = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src")
)
_WORK = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "work")
)
import sys

sys.path.insert(0, _SRC)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from game_dev_spot_bench import cloud_generate, hit, score_answer

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _mnemosis_contexts(dataset, questions):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for memory in dataset:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.8 if memory["kind"] == "semantic" else 0.6,
        )
    contexts = {}
    for question in questions:
        results = engine.recall(question["q"], top_k=4)
        rows = [r.item.content for r in results]
        hint = engine.temporal_hint(question["q"])
        if hint:
            rows = [hint] + rows
        contexts[question["q"]] = rows
    return contexts


def _mem0_contexts(dataset, questions, db_name):
    os.environ["MEM0_TELEMETRY"] = "False"
    with open(
        r"C:\Users\asus\plugins\image-viewer\scripts\vision_config.json",
        encoding="utf-8",
    ) as handle:
        cfg = json.load(handle)
    from mem0 import Memory

    db_path = os.path.join(_WORK, db_name)
    if os.path.isdir(db_path):
        shutil.rmtree(db_path)
    config = {
        "llm": {
            "provider": "openai",
            "config": {
                "model": cfg["model"],
                "api_key": cfg["api_key"],
                "openai_base_url": cfg["base_url"],
                "temperature": 0,
            },
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-v3",
                "api_key": cfg["api_key"],
                "openai_base_url": cfg["base_url"],
            },
        },
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": db_name,
                "path": db_path,
                "on_disk": True,
                "embedding_model_dims": 1024,
            },
        },
        "history_db_path": os.path.join(_WORK, db_name + "_history.db"),
    }
    memory = Memory.from_config(config)
    for entry in dataset:
        memory.add(entry["content"], user_id="u1", infer=False)
    contexts = {}
    for question in questions:
        resp = memory.search(
            question["q"], filters={"user_id": "u1"}, top_k=4
        )
        results = resp.get("results", [])
        contexts[question["q"]] = [
            r.get("memory", "") if isinstance(r, dict) else str(r)
            for r in results
        ]
    return contexts


def _answer_all(contexts, questions):
    answers = {}
    for project, rows in contexts.items():
        answers[project] = {}
        for question in questions:
            prompt = (
                "只根据下面的记忆回答，不要编造。"
                "如果记忆里没有答案，就回答：不知道。\n\n"
                "记忆：\n"
                + "\n".join(f"- {text}" for text in rows[question["q"]])
                + f"\n\n问题：{question['q']}"
            )
            try:
                answers[project][question["q"]] = cloud_generate(prompt)
            except Exception as exc:  # noqa: BLE001
                answers[project][question["q"]] = f"<error: {exc}>"
            print(
                f"  [{project}] {question['q'][:22]} done",
                flush=True,
            )
    return answers


def _dim_summary(pairs, questions):
    by_dim = {}
    for question in questions:
        by_dim.setdefault(question["dim"], []).append(
            1 if pairs[question["q"]] else 0
        )
    total = sum(value for values in by_dim.values() for value in values)
    per_dim = {
        dim: round(sum(values) / len(values), 3)
        for dim, values in by_dim.items()
    }
    return total, per_dim


def run_spot(
    *,
    domain,
    dataset,
    questions,
    db_name,
    out_name,
    skip_answers=False,
) -> int:
    os.makedirs(_WORK, exist_ok=True)
    contexts = {
        "mnemosis": _mnemosis_contexts(dataset, questions),
        "mem0": _mem0_contexts(dataset, questions, db_name),
    }
    retrieval = {}
    for project, rows in contexts.items():
        pairs = {q["q"]: hit(rows[q["q"]], q) for q in questions}
        total, per_dim = _dim_summary(pairs, questions)
        retrieval[project] = {"total": total, "per_dim": per_dim}
        print("retrieval", project, total, per_dim)
    out = {
        "domain": domain,
        "dimensions": [q["dim"] for q in questions],
        "contexts": contexts,
        "retrieval": retrieval,
    }
    if not skip_answers:
        answers = _answer_all(contexts, questions)
        out["answers_cloud"] = answers
        accuracy = {}
        for project, rows in answers.items():
            pairs = {q["q"]: score_answer(rows[q["q"]], q) for q in questions}
            total, per_dim = _dim_summary(pairs, questions)
            accuracy[project] = {"total": total, "per_dim": per_dim}
            print("accuracy_cloud", project, total, per_dim)
        out["accuracy_cloud"] = accuracy
    path = os.path.join(_WORK, out_name)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    return 0
