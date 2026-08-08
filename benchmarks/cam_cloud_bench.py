"""CAM official repo end-to-end retest with cloud qwen3.7-plus.

Same real CAM pipeline (graph build + Explorer prune-and-grow) as
``cam_locomo_bench.py``, but the LLM (both graph inference and answering)
is switched to the user-deployed DashScope qwen3.7-plus via the OpenAI
compatible endpoint. Embeddings stay on local Ollama nomic-embed-text so the
graph construction itself is unchanged.

Run from an empty work dir (CAM writes ./super_graphs relative to CWD):
    cd work/cam_cloud_run && python <repo>/benchmarks/cam_cloud_bench.py
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

import numpy as np  # noqa: E402

from locomo_bench import generate_dataset  # noqa: E402
from compare_with_models import score_answer  # noqa: E402
from model_x_project import select_questions  # noqa: E402


_CONFIG = os.path.join(
    "C:\\Users\\asus",
    "plugins",
    "image-viewer",
    "scripts",
    "vision_config.json",
)


def _cloud_config() -> dict:
    with open(_CONFIG, encoding="utf-8") as handle:
        cfg = json.load(handle)
    return {
        "api_key": cfg["api_key"],
        "base_url": cfg["base_url"],
        "model": cfg.get("model", "qwen3.7-plus"),
    }


def main() -> int:
    run_dir = os.path.join(_WORK, "cam_cloud_run")
    os.makedirs(run_dir, exist_ok=True)
    os.chdir(run_dir)
    keyfile = os.path.join(run_dir, "openai_key.txt")
    cloud = _cloud_config()
    with open(keyfile, "w", encoding="utf-8") as handle:
        handle.write(cloud["api_key"])

    # CAM's Explorer imports `tools.utils` while other modules import
    # `tasks.tools.utils`; both resolve to SEPARATE module copies because
    # `prototype/tasks` is on sys.path. Patch BOTH so every OpenAI client
    # routes chat completions to the cloud and embeddings stay local.
    from tasks.tools.utils import OpenAIClient as TasksOpenAIClient  # noqa: E402
    from tools.utils import OpenAIClient as ToolsOpenAIClient  # noqa: E402

    # Route only chat completions to the cloud; keep embeddings local.
    def _make_dual_init(orig_init):
        def _dual(self, key_path, model):
            with open(key_path, "r", encoding="utf-8") as handle:
                key = handle.read().strip()
            orig_init(self, key_path, model)
            from openai import OpenAI as _OpenAI

            self.cloud_client = _OpenAI(
                api_key=cloud["api_key"], base_url=cloud["base_url"]
            )
            self.local_embed_client = _OpenAI(
                api_key="ollama", base_url="http://127.0.0.1:11434/v1"
            )
            self.model = model

        return _dual

    def _cloud_send(self, prompt, max_tokens, temperature):
        response = self.cloud_client.chat.completions.create(
            model=cloud["model"],
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return response.choices[0].message.content

    def _local_embed(self, text, model):
        text = text.replace("\n", " ")
        return (
            self.local_embed_client.embeddings.create(
                input=[text], model=model
            )
            .data[0]
            .embedding
        )

    for cls in (TasksOpenAIClient, ToolsOpenAIClient):
        cls.__init__ = _make_dual_init(cls.__init__)
        cls.send_request = _cloud_send
        cls.get_embedding = _local_embed

    from constructivist_memory import CAM  # noqa: E402
    from tasks.question_answering import Explorer  # noqa: E402

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
        model=cloud["model"],
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
        model=cloud["model"],
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
            f"  [CAM-cloud] {question['q'][:42]:44s} score={score:.2f} "
            f"({took:.1f}s)",
            flush=True,
        )

    report = {
        "system": "CAM 官方仓库（云端 qwen3.7-plus 推理/作答）",
        "model": cloud["model"],
        "n": len(questions),
        "accuracy": round(hits / len(questions), 3),
        "retrieval_hit5": round(retrieval_hits5 / len(questions), 3),
        "embed_seconds": round(embed_seconds, 1),
        "build_seconds": round(build_seconds, 1),
        "details": details,
    }
    out = os.path.join(_BENCH, "results", "cam_official_v2_cloud.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
