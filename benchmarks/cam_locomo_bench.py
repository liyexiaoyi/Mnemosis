"""Real benchmark: official CAM repo (rui9812/CAM, NeurIPS 2025).

CAM is a constructivist hierarchical graph memory. This script runs the
*actual* repository code against the same 12 LoCoMo questions used in the
model x project matrix, with local models:

  - embeddings: Ollama nomic-embed-text via the OpenAI-compatible endpoint;
  - graph:      CAM.build_memory() (real code), level 0 only
                (max_hierarchy_level=0, no LLM summarization);
  - inference:  CAM Explorer prune-and-grow with Ollama qwen2.5:3b;
  - scoring:    same score_answer token rule as the matrix.

Run from an empty work dir (CAM writes ./super_graphs relative to CWD):
    cd work/cam_run && python <repo>/benchmarks/cam_locomo_bench.py
"""

from __future__ import annotations

import json
import os
import sys
import time

os.environ["OPENAI_BASE_URL"] = "http://127.0.0.1:11434/v1"
os.environ["OPENAI_API_KEY"] = "ollama"

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_CAM = os.path.normpath(
    os.path.join(_BENCH, "..", "..", "work", "gh_repos", "CAM")
)
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)
sys.path.insert(0, os.path.join(_CAM, "prototype"))
sys.path.insert(0, os.path.join(_CAM, "prototype", "tasks"))

import numpy as np
from compare_with_models import score_answer
from locomo_bench import generate_dataset
from model_x_project import select_questions


def main() -> int:
    run_dir = os.path.join(_WORK, "cam_run")
    os.makedirs(run_dir, exist_ok=True)
    os.chdir(run_dir)
    keyfile = os.path.join(run_dir, "openai_key.txt")
    with open(keyfile, "w", encoding="utf-8") as handle:
        handle.write("ollama")

    from constructivist_memory import CAM
    from tasks.question_answering import Explorer

    dataset = generate_dataset(seed=42, sessions=24, events_per_session=5)
    questions = select_questions(dataset)
    memories = dataset["facts"] + dataset["events"]
    metadata = [
        {
            "chunk_id": i,
            "text": m["content"],
            "gist": "",
            "entity_concepts": m.get("cues", []),
            "doc_id": "locomo",
        }
        for i, m in enumerate(memories)
    ]

    cam = CAM(
        dataset="locomo",
        threshold=0.55,
        weight=0.6,
        sigma=1.0,
        top_k=10,
        api_key_path=keyfile,
        model="qwen2.5:3b",
        embedding_model="nomic-embed-text",
        max_cluster_size=12,
        summary_field="text",
    )
    t0 = time.perf_counter()
    embeddings = np.stack(
        [
            np.array(cam.client.obtain_embedding(m["content"]), dtype=np.float32)
            for m in memories
        ],
        axis=0,
    )
    embed_seconds = time.perf_counter() - t0
    t0 = time.perf_counter()
    cam.build_memory(
        "locomo",
        metadata,
        embeddings,
        doc_mask=None,
        max_hierarchy_level=0,
    )
    build_seconds = time.perf_counter() - t0

    explorer = Explorer(
        dataset="locomo",
        book_title="locomo",
        api_key_path=keyfile,
        model="qwen2.5:3b",
        embedding_model="nomic-embed-text",
        text_field="text",
        top_k=10,
    )
    hits = 0
    retrieval_hits5 = 0
    details = []
    for question in questions:
        start = time.perf_counter()
        prediction, passages = explorer.run(
            question["q"], mode="GE", max_exploration_turns=3, tolerance=1
        )
        took = time.perf_counter() - start
        score = score_answer(prediction, question["answer"])
        hits += int(score >= 1.0)
        passage_texts = [txt for _, txt in passages]
        expected = question["expected"]
        retrieval_hits5 += int(
            bool(expected) and any(exp in passage_texts for exp in expected)
        )
        details.append(
            {
                "kind": question["kind"],
                "question": question["q"],
                "prediction": prediction,
                "expected": question["answer"],
                "score": round(score, 3),
                "seconds": round(took, 2),
                "passage_count": len(passage_texts),
                "retrieval_hit5": bool(expected)
                and any(exp in passage_texts for exp in expected),
            }
        )
        print(
            f"  [CAM] {question['q'][:42]:44s} score={score:.2f} "
            f"({took:.1f}s)",
            flush=True,
        )

    report = {
        "system": "CAM 官方仓库 (rui9812/CAM, NeurIPS 2025)",
        "n": len(questions),
        "accuracy": round(hits / len(questions), 3),
        "retrieval_hit5": round(retrieval_hits5 / len(questions), 3),
        "embed_seconds": round(embed_seconds, 1),
        "build_seconds": round(build_seconds, 1),
        "details": details,
    }
    out = os.path.join(_BENCH, "results", "cam_official.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
