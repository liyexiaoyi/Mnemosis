"""Research-notes spot-check (round 257): Mnemosis vs mem0 official ONLY.

New domain (科研笔记, Chinese + English mixed) and 10 new dimensions:

  论文档案 / 引用信息 / 实验参数 / 实验结果 / 数据集 /
  会议截稿 / 代码路径 / 合作者 / 审稿意见 / 基金申报

Real installs: Mnemosis (this repo) and mem0ai 2.0.17 official (cloud
qwen3.7-plus LLM + text-embedding-v3, qdrant local). Same memories,
same questions, top-4 contexts. Answering: cloud qwen3.7-plus +
DeepSeek V4 Flash (agent answers written from exact contexts).
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from game_dev_spot_bench import cloud_generate, hit, score_answer

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

DATASET = [
    {
        "content": "论文《Retrieval-Augmented Memory for Agents》投在 ACL 2026，第一作者是李默。",
        "kind": "semantic",
        "cues": ["论文", "ACL 2026"],
    },
    {
        "content": "论文 DOI 是 10.1145/1234567，Google Scholar 引用数 128。",
        "kind": "semantic",
        "cues": ["DOI", "引用"],
    },
    {
        "content": "对比实验：记忆增强模型在 LoCoMo 上的 Acc 是 0.91，基线只有 0.83。",
        "kind": "semantic",
        "cues": ["实验", "LoCoMo"],
    },
    {
        "content": "训练超参：batch size 32，学习率 2e-5，max length 2048，共 3 个 epoch。",
        "kind": "semantic",
        "cues": ["超参", "batch"],
    },
    {
        "content": "使用数据集 LongBench-zh 与 HotpotQA 做消融，LongBench-zh 有 2.3 万条。",
        "kind": "semantic",
        "cues": ["数据集", "LongBench"],
    },
    {
        "content": "EMNLP 2026 摘要截稿时间是 5 月 15 日，全文截稿 5 月 22 日。",
        "kind": "semantic",
        "cues": ["EMNLP", "截稿"],
    },
    {
        "content": "复现代码在 github.com/limo/ram-agent，主脚本 scripts/run_ablation.py。",
        "kind": "semantic",
        "cues": ["代码", "github"],
    },
    {
        "content": "合作者王宁在清华，负责评估；陈雨在浙大，负责数据分析。",
        "kind": "semantic",
        "cues": ["合作者", "王宁"],
    },
    {
        "content": "审稿意见 R1：需要补充跨语言实验，R2：希望公开训练代码。",
        "kind": "episodic",
        "cues": ["审稿", "R1"],
    },
    {
        "content": "基金申请：国家自然科学基金青年项目，预算 30 万，8 月 20 日截止。",
        "kind": "semantic",
        "cues": ["基金", "青年项目"],
    },
    {
        "content": "论文 arxiv 编号 2603.12345，v2 更新了附录的复杂度分析。",
        "kind": "semantic",
        "cues": ["arxiv", "2603.12345"],
    },
    {
        "content": "5月8日组会决定：主实验从 3 个数据集扩到 5 个，新增 MS MARCO。",
        "kind": "episodic",
        "cues": ["2026-05-08", "组会"],
    },
    {
        "content": "消融实验显示去掉重放机制 Acc 掉 0.04，去掉间隔复习掉 0.03。",
        "kind": "semantic",
        "cues": ["消融", "重放"],
    },
    {
        "content": "算力申请：A100 卡 4 张，预计使用 3000 卡时，机时费约 1.2 万元。",
        "kind": "semantic",
        "cues": ["算力", "A100"],
    },
    {
        "content": "5月20日实验日志：混合训练后验证集 loss 从 0.62 降到 0.55。",
        "kind": "episodic",
        "cues": ["2026-05-20", "实验日志"],
    },
    {
        "content": "写作计划：intro 部分 6 月 1 日前完成，related work 6 月 5 日前。",
        "kind": "semantic",
        "cues": ["写作", "intro"],
    },
    {
        "content": "投稿系统 OpenReview 编号 2605-abc123，需要 5 月 30 日前回复审稿意见。",
        "kind": "episodic",
        "cues": ["OpenReview", "2605-abc123"],
    },
    {
        "content": "实验室服务器登录：node01.lab.edu.cn，用户 limo，端口 22。",
        "kind": "semantic",
        "cues": ["服务器", "node01"],
    },
]


QUESTIONS = [
    {
        "dim": "论文档案",
        "q": "《Retrieval-Augmented Memory for Agents》投在哪个会议？第一作者是谁？",
        "answer": "ACL 2026，李默",
        "terms": ["ACL", "李默"],
    },
    {
        "dim": "引用信息",
        "q": "论文的 DOI 是什么？引用数多少？",
        "answer": "10.1145/1234567，128",
        "terms": ["10.1145/1234567", "128"],
    },
    {
        "dim": "实验参数",
        "q": "训练时的 batch size 和学习率是多少？",
        "answer": "batch 32，学习率 2e-5",
        "terms": ["32", "2e-5"],
    },
    {
        "dim": "实验结果",
        "q": "记忆增强模型在 LoCoMo 上的准确率是多少？基线呢？",
        "answer": "0.91 和 0.83",
        "terms": ["0.91", "0.83"],
    },
    {
        "dim": "数据集",
        "q": "消融用到了哪两个数据集？LongBench-zh 有多少条？",
        "answer": "LongBench-zh 和 HotpotQA，2.3 万条",
        "terms": ["LongBench", "HotpotQA"],
    },
    {
        "dim": "会议截稿",
        "q": "EMNLP 2026 摘要截稿是什么时候？",
        "answer": "5 月 15 日",
        "terms": ["15"],
    },
    {
        "dim": "代码路径",
        "q": "复现代码在哪里？消融主脚本叫什么？",
        "answer": "github.com/limo/ram-agent，run_ablation.py",
        "terms": ["ram-agent", "run_ablation"],
    },
    {
        "dim": "合作者",
        "q": "王宁在哪个单位？负责什么？",
        "answer": "清华，负责评估",
        "terms": ["清华", "评估"],
    },
    {
        "dim": "审稿意见",
        "q": "审稿人 R2 提了什么要求？",
        "answer": "公开训练代码",
        "terms": ["训练代码"],
    },
    {
        "dim": "基金申报",
        "q": "基金申请是什么类型？预算多少？什么时候截止？",
        "answer": "青年项目，30 万，8 月 20 日",
        "terms": ["青年", "30", "20"],
    },
]


def _mnemosis_contexts() -> dict[str, list[str]]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for memory in DATASET:
        engine.remember(
            memory["content"],
            kind=MemoryKind(memory["kind"]),
            source=user,
            cues=memory.get("cues"),
            importance=0.8 if memory["kind"] == "semantic" else 0.6,
        )
    contexts: dict[str, list[str]] = {}
    for question in QUESTIONS:
        results = engine.recall(question["q"], top_k=4)
        contexts[question["q"]] = [r.item.content for r in results]
    return contexts


def _mem0_contexts() -> dict[str, list[str]]:
    os.environ["MEM0_TELEMETRY"] = "False"
    with open(
        r"C:\Users\asus\plugins\image-viewer\scripts\vision_config.json",
        encoding="utf-8",
    ) as handle:
        cfg = json.load(handle)
    from mem0 import Memory

    db_path = os.path.join(_WORK, "research_mem0db")
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
                "collection_name": "research_spot",
                "path": db_path,
                "on_disk": True,
                "embedding_model_dims": 1024,
            },
        },
        "history_db_path": os.path.join(_WORK, "research_mem0_history.db"),
    }
    memory = Memory.from_config(config)
    for entry in DATASET:
        memory.add(entry["content"], user_id="u1", infer=False)
    contexts: dict[str, list[str]] = {}
    for question in QUESTIONS:
        resp = memory.search(
            question["q"], filters={"user_id": "u1"}, top_k=4
        )
        results = resp.get("results", [])
        contexts[question["q"]] = [
            r.get("memory", "") if isinstance(r, dict) else str(r)
            for r in results
        ]
    return contexts


def _answer_all(contexts: dict) -> dict:
    answers: dict[str, dict] = {}
    for project, rows in contexts.items():
        answers[project] = {}
        for question in QUESTIONS:
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
                f"  [{project}] {question['q'][:24]} done",
                flush=True,
            )
    return answers


def _dim_summary(pairs: dict[str, bool]) -> tuple[int, dict[str, float]]:
    by_dim: dict[str, list[int]] = {}
    for question in QUESTIONS:
        by_dim.setdefault(question["dim"], []).append(
            1 if pairs[question["q"]] else 0
        )
    total = sum(value for values in by_dim.values() for value in values)
    per_dim = {
        dim: round(sum(values) / len(values), 3)
        for dim, values in by_dim.items()
    }
    return total, per_dim


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    os.makedirs(_WORK, exist_ok=True)
    contexts = {
        "mnemosis": _mnemosis_contexts(),
        "mem0": _mem0_contexts(),
    }
    retrieval: dict[str, dict] = {}
    for project, rows in contexts.items():
        pairs = {q["q"]: hit(rows[q["q"]], q) for q in QUESTIONS}
        total, per_dim = _dim_summary(pairs)
        retrieval[project] = {"total": total, "per_dim": per_dim}
        print("retrieval", project, total, per_dim)
    out: dict = {
        "domain": "科研笔记",
        "dimensions": [q["dim"] for q in QUESTIONS],
        "contexts": contexts,
        "retrieval": retrieval,
    }
    if not args.skip_answers:
        answers = _answer_all(contexts)
        out["answers_cloud"] = answers
        accuracy: dict[str, dict] = {}
        for project, rows in answers.items():
            pairs = {q["q"]: score_answer(rows[q["q"]], q) for q in QUESTIONS}
            total, per_dim = _dim_summary(pairs)
            accuracy[project] = {"total": total, "per_dim": per_dim}
            print("accuracy_cloud", project, total, per_dim)
        out["accuracy_cloud"] = accuracy
    path = os.path.join(_WORK, "research_spot.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
