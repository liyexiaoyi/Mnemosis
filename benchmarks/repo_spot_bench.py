"""Dev-repo spot-check (round 259): Mnemosis vs mem0 official ONLY.

New domain (代码仓库/开发日志), closest to Mnemosis's own use case.
Chinese dev notes mixed with English git terms, SHAs and versions.
10 new dimensions:

  提交记录 / 分支管理 / Issue跟踪 / PR审查 / CI状态 /
  依赖版本 / 发布记录 / 环境配置 / 代码规范 / 里程碑
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402

from game_dev_spot_bench import cloud_generate, hit, score_answer  # noqa: E402


DATASET = [
    {
        "content": "仓库 memory-core 的默认分支是 main，开发分支是 dev/next，发布分支是 release/1.x。",
        "kind": "semantic",
        "cues": ["分支", "memory-core"],
    },
    {
        "content": "6月3日提交 7f3a9c2：修复召回时 top_k 为 0 崩溃，关联 issue #142。",
        "kind": "episodic",
        "cues": ["7f3a9c2", "提交"],
    },
    {
        "content": "issue #142：当 top_k 传 0 时 recall 抛 IndexError，优先级 P1。",
        "kind": "semantic",
        "cues": ["#142", "issue"],
    },
    {
        "content": "PR #88 加了 MCP 工具 concept_cover，评审意见：补 3 个测试再合。",
        "kind": "episodic",
        "cues": ["PR #88", "concept_cover"],
    },
    {
        "content": "CI 流水线：单元测试（ubuntu + windows）、覆盖率门禁 90%、publish 到 PyPI。",
        "kind": "semantic",
        "cues": ["CI", "覆盖率"],
    },
    {
        "content": "依赖版本：pydantic 2.13.4、numpy 2.4.6、httpx 0.28.1，Python 要求 3.10+。",
        "kind": "semantic",
        "cues": ["依赖", "pydantic"],
    },
    {
        "content": "v0.16.40 发布于 8 月 9 日，核心变化：记忆快照、概念覆盖、学习闭环。",
        "kind": "episodic",
        "cues": ["v0.16.40", "发布"],
    },
    {
        "content": "环境配置：开发用 uv，测试数据库用内存版，CI 用 PostgreSQL 15。",
        "kind": "semantic",
        "cues": ["环境", "uv"],
    },
    {
        "content": "代码规范：ruff 配置 line-length 88，类型检查 mypy --strict，提交前跑 pre-commit。",
        "kind": "semantic",
        "cues": ["ruff", "规范"],
    },
    {
        "content": "里程碑 M3（8 月底）：MCP 工具 60+、全测评 170+、文档中文版完成。",
        "kind": "semantic",
        "cues": ["里程碑", "M3"],
    },
    {
        "content": "6月5日合并 PR #89：修复 context_pack 过滤概念覆盖理由，提交号 91ab4ef。",
        "kind": "episodic",
        "cues": ["91ab4ef", "PR #89"],
    },
    {
        "content": "issue #150：中文长问题漏检索，6月8日标记为已复现，指派给李默。",
        "kind": "episodic",
        "cues": ["#150", "issue"],
    },
    {
        "content": "6月9日 CI 变红：Windows 上 pytest 花 88 秒超时，改成 120 秒后恢复。",
        "kind": "episodic",
        "cues": ["2026-06-09", "CI"],
    },
    {
        "content": "发布流程：打 tag v*，自动生成 changelog，然后 publish 到 PyPI 和 npm。",
        "kind": "semantic",
        "cues": ["发布流程", "tag"],
    },
    {
        "content": "6月10日把 Embedder 接口拆成 protocol，改动文件 12 个，测试全绿。",
        "kind": "episodic",
        "cues": ["2026-06-10", "重构"],
    },
    {
        "content": "依赖升级计划：9 月前把 pydantic 升到 2.14，先跑兼容矩阵。",
        "kind": "semantic",
        "cues": ["升级", "pydantic"],
    },
    {
        "content": "文档站点 docs.memory-core.dev，改版后用 mike 发布到 gh-pages。",
        "kind": "semantic",
        "cues": ["文档", "mike"],
    },
    {
        "content": "6月12日热修 v0.16.39：回滚 embedding_model_dims 校验，避免旧库不兼容。",
        "kind": "episodic",
        "cues": ["2026-06-12", "热修"],
    },
    {
        "content": "性能基线：10 万条记忆召回 p95 是 42ms，目标 8 月底压到 30ms。",
        "kind": "semantic",
        "cues": ["性能", "p95"],
    },
    {
        "content": "6月13日新增 benchmark 目录规范：每个工具必须有 eval + render 脚本。",
        "kind": "episodic",
        "cues": ["2026-06-13", "benchmark"],
    },
    {
        "content": "issue #160：MCP server 在 Windows 上 stdio 中文乱码，计划 6 月修。",
        "kind": "episodic",
        "cues": ["#160", "乱码"],
    },
    {
        "content": "6月14日 release/1.x 分支冻结，只接受 hotfix。",
        "kind": "episodic",
        "cues": ["2026-06-14", "冻结"],
    },
    {
        "content": "6月15日清掉 23 个陈旧分支，只留 dev/next、main、release/1.x。",
        "kind": "episodic",
        "cues": ["2026-06-15", "分支"],
    },
    {
        "content": "里程碑 M2 已达成：170 维矩阵、307 单元测试、mem0 官方同基准对比全绿。",
        "kind": "semantic",
        "cues": ["M2", "里程碑"],
    },
]


QUESTIONS = [
    {
        "dim": "提交记录",
        "q": "修复 top_k 为 0 崩溃的提交号是多少？关联哪个 issue？",
        "answer": "7f3a9c2，issue #142",
        "terms": ["7f3a9c2", "142"],
    },
    {
        "dim": "分支管理",
        "q": "仓库的默认分支和开发分支分别是什么？",
        "answer": "main 和 dev/next",
        "terms": ["main", "dev/next"],
    },
    {
        "dim": "Issue跟踪",
        "q": "issue #150 是什么问题？指派给谁？",
        "answer": "中文长问题漏检索，李默",
        "terms": ["漏检索", "李默"],
    },
    {
        "dim": "PR审查",
        "q": "PR #88 加了什么？评审要求补什么再合？",
        "answer": "concept_cover，补 3 个测试",
        "terms": ["concept_cover", "测试"],
    },
    {
        "dim": "CI状态",
        "q": "6月9日 CI 为什么变红？怎么恢复的？",
        "answer": "Windows 测试 88 秒超时，改成 120 秒",
        "terms": ["88", "120"],
    },
    {
        "dim": "依赖版本",
        "q": "pydantic 和 numpy 的版本分别是多少？",
        "answer": "pydantic 2.13.4，numpy 2.4.6",
        "terms": ["2.13.4", "2.4.6"],
    },
    {
        "dim": "发布记录",
        "q": "v0.16.40 什么时候发布的？核心变化是什么？",
        "answer": "8 月 9 日，快照/概念覆盖/学习闭环",
        "terms": ["16.40", "概念覆盖"],
    },
    {
        "dim": "环境配置",
        "q": "开发用什么包管理器？CI 用什么数据库？",
        "answer": "uv，PostgreSQL 15",
        "terms": ["uv", "PostgreSQL"],
    },
    {
        "dim": "代码规范",
        "q": "ruff 配置的行长度是多少？",
        "answer": "88",
        "terms": ["88"],
    },
    {
        "dim": "里程碑",
        "q": "M3 里程碑什么时候完成？要达成什么？",
        "answer": "8 月底，MCP 60+、全测评 170+、中文文档",
        "terms": ["M3", "170"],
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

    db_path = os.path.join(_WORK, "repo_mem0db")
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
                "collection_name": "repo_spot",
                "path": db_path,
                "on_disk": True,
                "embedding_model_dims": 1024,
            },
        },
        "history_db_path": os.path.join(_WORK, "repo_mem0_history.db"),
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
                f"  [{project}] {question['q'][:22]} done",
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
        "domain": "代码仓库",
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
    path = os.path.join(_WORK, "repo_spot.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
