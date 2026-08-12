"""Real benchmark: official TencentDB Agent Memory (TencentCloud, MIT).

The Tencent gateway runs locally (standalone mode, SQLite + BM25, Ollama
qwen2.5:3b for L1 extraction). We ingest the same 144 LoCoMo memories as
conversations, let its L1 extraction pipeline run, then search the same 12
questions, ground qwen2.5:3b in the retrieved memories and score with the
same `score_answer` rule.
"""

from __future__ import annotations

import argparse
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

from cloud_qwen_matrix import cloud_generate
from compare_with_models import score_answer
from locomo_bench import generate_dataset
from model_x_project import select_questions
from tencentdb_agent_memory import MemoryClient

ENDPOINT = "http://127.0.0.1:8420"


def _health() -> dict:
    with urllib.request.urlopen(ENDPOINT + "/health", timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wait-seconds", type=int, default=120)
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="reuse the already-ingested memory store (pipeline state persists)",
    )
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "tencent_official.json"),
    )
    args = parser.parse_args()
    client = MemoryClient(
        endpoint=ENDPOINT, api_key="local", service_id="default"
    )
    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    questions = select_questions(dataset)
    memories = dataset["facts"] + dataset["events"]

    ingest_seconds = 0.0
    if not args.skip_ingest:
        t0 = time.perf_counter()
        for i, memory in enumerate(memories):
            client.add_conversation(
                session_id=f"locomo-s{i}",
                messages=[{"role": "user", "content": memory["content"]}],
                user_id="u1",
            )
        ingest_seconds = time.perf_counter() - t0
        print(f"ingested {len(memories)} conversations in {ingest_seconds:.1f}s",
              flush=True)

    # wait for the L1 extraction pipeline
    deadline = time.time() + args.wait_seconds
    while time.time() < deadline:
        h = _health()
        h["services"]["pipelineWorker"]["tasksConsumed"]
        completed = h["services"]["pipelineWorker"]["tasksCompleted"]
        failed = h["services"]["pipelineWorker"]["tasksFailed"]
        if completed + failed >= len(memories):
            break
        time.sleep(5)
    h = _health()
    pw = h["services"]["pipelineWorker"]
    print(
        f"pipeline: consumed={pw['tasksConsumed']} completed={pw['tasksCompleted']} "
        f"failed={pw['tasksFailed']}",
        flush=True,
    )

    def context_text(hits: dict) -> list[str]:
        items = hits.get("items", [])
        out = []
        for item in items:
            text = item.get("content") or item.get("memory") or ""
            if text:
                out.append(text)
        return out

    retrieval_hits5 = 0
    answer_hits = 0
    details = []
    for question in questions:
        hits = client.search_atomic(
            query=question["q"], limit=5, user_id="u1"
        )
        contexts = context_text(hits)
        expected = question["expected"]
        retrieval_hits5 += int(
            bool(expected) and any(e in contexts for e in expected)
        )
        prompt = (
            "Answer using ONLY the memory context below. "
            "If the context lacks the answer, answer 'unknown'.\n\n"
            "Context:\n" + "\n".join(f"- {c}" for c in contexts) +
            f"\n\nQuestion: {question['q']}"
        )
        start = time.perf_counter()
        try:
            answer = cloud_generate(prompt)
        except Exception as exc:  # noqa: BLE001
            answer = f"<error: {exc}>"
        took = time.perf_counter() - start
        score = score_answer(answer, question["answer"])
        answer_hits += int(score >= 1.0)
        details.append(
            {
                "kind": question["kind"],
                "question": question["q"],
                "answer": answer,
                "expected": question["answer"],
                "score": round(score, 3),
                "retrieval_hit5": bool(expected)
                and any(e in contexts for e in expected),
                "context_count": len(contexts),
                "seconds": round(took, 2),
            }
        )
        print(
            f"  [Tencent] {question['q'][:40]:42s} score={score:.2f} "
            f"retr5={details[-1]['retrieval_hit5']} ({took:.1f}s)",
            flush=True,
        )

    report = {
        "system": "TencentDB Agent Memory 官方仓库（本地服务）",
        "n": len(questions),
        "accuracy": round(answer_hits / len(questions), 3),
        "retrieval_hit5": round(retrieval_hits5 / len(questions), 3),
        "ingest_seconds": round(ingest_seconds, 1),
        "pipeline": pw,
        "details": details,
    }
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
