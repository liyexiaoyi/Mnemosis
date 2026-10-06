"""Actual A/B/C retrieval with model provenance and frozen-response replay."""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import replace
from datetime import datetime
import json
from pathlib import Path
import sqlite3
import time

from mnemosis import MemoryEngine
from mnemosis.embedding import CallableEmbedder
from mnemosis.evidence_annotation import ModelReply, SkippedEvidence, SupportBatchReply, SupportReplies
from mnemosis.evidence_recall import _serialize, select_from_snapshot
from mnemosis.ollama_evidence import OllamaEvidenceAnnotator
from mnemosis.types import MemoryItem, RecallResult
from mnemosis.vector_index import VectorIndex
from verification_utils import ReadOnlyGuard


def pack(results):
    return [{"item": r.item.to_dict(), "score": r.score, "reasons": list(r.reasons), "confident": r.confident}
            for r in results]


def unpack(results):
    return tuple(RecallResult(MemoryItem.from_dict(r["item"]), r["score"], list(r["reasons"]), r["confident"])
                 for r in results)


def metrics(results, expected):
    actual = [r.item.content for r in results]
    wanted = set(expected)
    return {"all": bool(wanted) and wanted.issubset(actual),
            "hit1": bool(wanted) and bool(actual) and actual[0] in wanted,
            "any": bool(wanted.intersection(actual))}


def run_case(engine, question, provider, *, now, top_k=5, candidate_limit=100,
             relevance_weight=.5, search_budget=10000):
    query = question["q"]
    start = time.monotonic()
    a = engine.recall(query, top_k=top_k, now=now, read_only=True, lexical_policy="inflection")
    a_seconds = time.monotonic() - start
    start = time.monotonic()
    with engine._lock:
        pool = tuple(deepcopy(engine.recall(query, top_k=candidate_limit, now=now,
                                           read_only=True, lexical_policy="inflection")))
    pool_seconds = time.monotonic() - start
    b = pool[:top_k]
    report = select_from_snapshot(query, pool, annotator=provider, top_k=top_k,
                                  relevance_weight=relevance_weight, search_budget=search_budget)
    report = replace(report, timings={**report.timings, "recall": pool_seconds,
                                      "total": report.timings["total"] + pool_seconds})
    expected = question.get("expected", [])
    return {"question": deepcopy(question), "top_k": top_k, "candidate_limit": candidate_limit,
        "relevance_weight": relevance_weight, "search_budget": search_budget,
        "A": {"results": pack(a), "seconds": a_seconds, "metrics": metrics(a, expected)},
        "B": {"results": pack(b), "seconds": pool_seconds, "pool_seconds": pool_seconds, "metrics": metrics(b, expected)},
        "C": {"results": pack(report.results), "seconds": report.timings["total"], "metrics": metrics(report.results, expected)},
        "candidates": pack(pool), "report": report.to_dict(), "model_replies": _serialize(report.model_replies)}


class ReplayAnnotator:
    budget_seconds = 60.

    def __init__(self, row):
        self.replies = [ModelReply(**v) for v in row["model_replies"]]
        self.skipped = tuple(SkippedEvidence(**v) for v in row["report"]["skipped"])

    def plan(self, query, *, deadline):
        return self.replies[0]

    def support(self, query, aspects, source_texts, *, deadline):
        batches = []
        for reply in self.replies[1:]:
            data = json.loads(reply.request["messages"][1]["content"])
            assert data["question"] == query
            assert data["aspects"] == [{"aspect_id": a.aspect_id, "description": a.description} for a in aspects]
            assert all(source_texts[key] == text for key, text in data["memories"].items())
            batches.append(SupportBatchReply(tuple(data["memories"]), reply))
        return SupportReplies(tuple(batches), self.skipped)


def replay_row(row):
    report = select_from_snapshot(row["question"]["q"], unpack(row["candidates"]),
        annotator=ReplayAnnotator(row), top_k=row["top_k"],
        relevance_weight=row["relevance_weight"], search_budget=row["search_budget"])
    return report.to_dict()


def state(engine, index):
    connections = [c for c in (getattr(engine.backend, "_conn", None), getattr(index, "_conn", None)) if c is not None]
    return deepcopy((sorted((i.to_dict() for i in engine.backend.list_items()), key=lambda i:i["id"]),
                     sorted(engine.backend.all_links()), list(engine._recall_log),
                     [list(c.iterdump()) for c in connections]))


def _public_engine(protocol, case, output, vectors):
    folder = output / case["name"]
    folder.mkdir()
    seed = Path(protocol["public_seed_root"]) / "runs" / case["name"] / "mnemosis-shared-input"
    for filename in ("memory.sqlite", "vectors.sqlite"):
        source = sqlite3.connect((seed / filename).as_uri() + "?mode=ro&immutable=1", uri=True)
        target = sqlite3.connect(folder / filename)
        try:
            source.backup(target)
        finally:
            source.close(); target.close()
    embedder = CallableEmbedder(lambda text: list(vectors[text]),
        fn_many=lambda texts: [list(vectors[t]) for t in texts], cache_key="frozen-real-nomic")
    index = VectorIndex(str(folder / "vectors.sqlite"), dim=768)
    return MemoryEngine(str(folder / "memory.sqlite"), embedder=embedder,
        vector_index=index, index_embedder=embedder, auto_warmup=False), index


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", required=True)
    parser.add_argument("--cases", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--mode", choices=("constructed", "public", "replay"), required=True)
    args = parser.parse_args(argv)
    protocol = json.loads(Path(args.protocol).read_text(encoding="utf8"))
    output = Path(args.output); output.mkdir(parents=True, exist_ok=False)
    if args.mode == "replay":
        rows = [json.loads(v) for v in Path(args.cases).read_text(encoding="utf8").splitlines() if v]
        for row in rows:
            actual = replay_row(row)
            assert {k:v for k,v in actual.items() if k != "timings"} == {
                k:v for k,v in row["report"].items() if k != "timings"}
        (output / "replay.json").write_text(json.dumps({"rows": len(rows), "exact_semantic_reports": True}), encoding="utf8")
        print(f"replayed {len(rows)} exact semantic reports", flush=True)
        return 0
    cases = json.loads(Path(args.cases).read_text(encoding="utf8"))
    vectors = json.loads(Path(protocol["embeddings"]).read_text(encoding="utf8")) if args.mode == "public" else None
    now = datetime.fromisoformat(protocol["now"])
    provider = OllamaEvidenceAnnotator(model=protocol["model"], base_url=protocol["base_url"])
    before_after, count = [], 0
    with (output / "results.jsonl").open("x", encoding="utf8") as log:
        for case in cases:
            if args.mode == "public":
                if case.get("source_index") not in (7,8,9):
                    continue
                engine, index = _public_engine(protocol, case, output, vectors)
            else:
                engine, index = MemoryEngine(auto_warmup=False), None
                for memory in case["memories"]:
                    engine.remember(memory["content"], created_at=now)
            try:
                before = state(engine, index)
                with ExitStack() as guards:
                    for connection in (getattr(engine.backend, "_conn", None), getattr(index, "_conn", None)):
                        if connection is not None:
                            guards.enter_context(ReadOnlyGuard(connection))
                    for question in case["questions"]:
                        row = run_case(engine, question, provider, now=now,
                            top_k=protocol["top_k"], candidate_limit=protocol["candidate_limit"],
                            relevance_weight=protocol["relevance_weight"], search_budget=protocol["search_budget"])
                        row.update(case=case["name"], split=case.get("split", "historical"))
                        log.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n"); log.flush()
                        count += 1
                        print(f"{count}: {case['name']} {row['report']['status']} {row['C']['seconds']:.2f}s", flush=True)
                assert state(engine, index) == before
                before_after.append({"case": case["name"], "full_state_equal": True})
            finally:
                engine.close()
    (output / "state-checks.json").write_text(json.dumps(before_after, indent=2), encoding="utf8")
    (output / "completion.json").write_text(json.dumps({"queries": count, "mode": args.mode, "complete": True}), encoding="utf8")
    print(f"complete: {count}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
