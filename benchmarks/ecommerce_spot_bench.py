"""E-commerce spot-check (round 256): Mnemosis vs mem0 official ONLY.

New domain (电商运营) and 10 new dimensions, unrelated to previous
benchmarks:

  商品档案 / 价格记忆 / 库存记忆 / 促销活动 / 客服反馈 / 物流异常 /
  供应商 / 平台规则 / 复购数据 / 竞品动态

Real installs: Mnemosis (this repo) and mem0ai 2.0.17 official (cloud
qwen3.7-plus LLM + text-embedding-v3, qdrant local). Same memories, same
questions, top-4 contexts. Answering: cloud qwen3.7-plus + DeepSeek V4
Flash (agent answers written from exact contexts).
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
        "content": "店铺《山野食集》主营坚果零食，核心商品是 SKU N-1001 混合坚果 500g。",
        "kind": "semantic",
        "cues": ["山野食集", "N-1001"],
    },
    {
        "content": "混合坚果 500g 日常售价 39.9 元，618 期间活动价 29.9 元。",
        "kind": "semantic",
        "cues": ["混合坚果", "价格"],
    },
    {
        "content": "核桃仁 250g 当前库存 1280 件，低于 500 件时触发补货提醒。",
        "kind": "semantic",
        "cues": ["核桃仁", "库存"],
    },
    {
        "content": "2026年6月1日开启满 99 减 20 活动，持续到 6 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-06-01", "满减"],
    },
    {
        "content": "6月5日客服收到 3 条反馈：包装袋破损，已给顾客补发并补偿 5 元券。",
        "kind": "episodic",
        "cues": ["2026-06-05", "客服"],
    },
    {
        "content": "6月8日圆通物流异常：发往杭州的包裹滞留 3 天，已升级加急处理。",
        "kind": "episodic",
        "cues": ["2026-06-08", "物流"],
    },
    {
        "content": "供应商 A 是核桃仁主供应商，账期 30 天，月供 2 吨。",
        "kind": "semantic",
        "cues": ["供应商", "核桃仁"],
    },
    {
        "content": "平台规则：标题里写“最低价”会被判违规下架，已提醒运营不要使用。",
        "kind": "semantic",
        "cues": ["平台规则", "最低价"],
    },
    {
        "content": "复购数据：6 月老客复购率 38%，比 5 月提高 5 个百分点。",
        "kind": "semantic",
        "cues": ["复购", "6月"],
    },
    {
        "content": "竞品 B 6月10日上了同款坚果 450g 卖 34.9 元，带 3 元无门槛券。",
        "kind": "episodic",
        "cues": ["2026-06-10", "竞品"],
    },
    {
        "content": "SKU N-1002 是每日坚果 25g×30 袋，售价 59.9 元。",
        "kind": "semantic",
        "cues": ["N-1002", "每日坚果"],
    },
    {
        "content": "仓库在嘉兴，发江浙沪默认中通，其他地区默认圆通。",
        "kind": "semantic",
        "cues": ["仓库", "物流"],
    },
    {
        "content": "6月12日运营决定把主图换成实拍图，点击率从 3.1% 升到 4.6%。",
        "kind": "episodic",
        "cues": ["2026-06-12", "主图"],
    },
    {
        "content": "退款规则：签收后 7 天内无理由退货，生鲜不支持。",
        "kind": "semantic",
        "cues": ["退款", "规则"],
    },
    {
        "content": "客服话术模板已更新：先道歉再补偿，避免顾客升级投诉。",
        "kind": "semantic",
        "cues": ["客服", "话术"],
    },
    {
        "content": "6月15日直播带货一场卖出 620 单，销售额 2.1 万元。",
        "kind": "episodic",
        "cues": ["2026-06-15", "直播"],
    },
    {
        "content": "备货计划：双 11 前把混合坚果库存提到 5000 件。",
        "kind": "semantic",
        "cues": ["备货", "双11"],
    },
    {
        "content": "会员体系：累计消费满 300 元送 10 元无门槛券。",
        "kind": "semantic",
        "cues": ["会员", "300"],
    },
]


QUESTIONS = [
    {
        "dim": "商品档案",
        "q": "山野食集的核心商品是什么？SKU 是多少？",
        "answer": "SKU N-1001 混合坚果 500g",
        "terms": ["N-1001", "混合坚果"],
    },
    {
        "dim": "价格记忆",
        "q": "混合坚果 500g 日常价和 618 活动价分别是多少？",
        "answer": "39.9 和 29.9",
        "terms": ["39.9", "29.9"],
    },
    {
        "dim": "库存记忆",
        "q": "核桃仁 250g 当前库存多少？低于多少件触发补货？",
        "answer": "1280 件，低于 500",
        "terms": ["1280", "500"],
    },
    {
        "dim": "促销活动",
        "q": "6 月的满减活动是什么？持续到什么时候？",
        "answer": "满 99 减 20，到 6 月 20 日",
        "terms": ["99", "20"],
    },
    {
        "dim": "客服反馈",
        "q": "6月5日顾客反馈了什么？怎么处理的？",
        "answer": "包装袋破损，补发并补偿 5 元券",
        "terms": ["破损", "补发"],
    },
    {
        "dim": "物流异常",
        "q": "发往杭州的包裹出了什么问题？",
        "answer": "滞留 3 天",
        "terms": ["滞留"],
    },
    {
        "dim": "供应商",
        "q": "核桃仁的主供应商是谁？账期多久？",
        "answer": "供应商 A，账期 30 天",
        "terms": ["供应商 A", "30"],
    },
    {
        "dim": "平台规则",
        "q": "标题里写什么词会被平台判违规？",
        "answer": "最低价",
        "terms": ["最低价"],
    },
    {
        "dim": "复购数据",
        "q": "6 月老客复购率是多少？比 5 月变化多少？",
        "answer": "38%，提高 5 个百分点",
        "terms": ["38", "5"],
    },
    {
        "dim": "竞品动态",
        "q": "竞品 B 6月10日上了什么产品？价格多少？",
        "answer": "同款坚果 450g，34.9 元",
        "terms": ["450", "34.9"],
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

    db_path = os.path.join(_WORK, "ecommerce_mem0db")
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
                "collection_name": "ecommerce_spot",
                "path": db_path,
                "on_disk": True,
                "embedding_model_dims": 1024,
            },
        },
        "history_db_path": os.path.join(_WORK, "ecommerce_mem0_history.db"),
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
        "domain": "电商运营",
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
    path = os.path.join(_WORK, "ecommerce_spot.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
