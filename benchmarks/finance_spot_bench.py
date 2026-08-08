"""Personal-finance spot-check (round 258): Mnemosis vs mem0 ONLY.

New domain (个人理财/家庭账本), harder setup: 24 memories with many
number/date distractors and deliberately fuzzy questions. 10 new dims:

  账户信息 / 收支记录 / 预算 / 投资持仓 / 贷款还款 /
  保险 / 票据凭证 / 月度总结 / 订阅扣费 / 家庭目标
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
        "content": "家庭共用一张招行卡 6222-****-8888，微信零钱和支付宝余额是分开记的。",
        "kind": "semantic",
        "cues": ["招行卡", "账户"],
    },
    {
        "content": "5月工资 18500 元 5 月 10 日到账，公积金 2100 元 5 月 12 日到账。",
        "kind": "episodic",
        "cues": ["2026-05-10", "工资"],
    },
    {
        "content": "5月水电费 436 元、燃气费 178 元、物业费 650 元，都在 5 月 18 日扣款。",
        "kind": "episodic",
        "cues": ["2026-05-18", "水电"],
    },
    {
        "content": "每月预算：吃饭 3000 元、交通 800 元、娱乐 1000 元、其他 1200 元。",
        "kind": "semantic",
        "cues": ["预算"],
    },
    {
        "content": "6月3日买理财 50000 元，年化 3.2%，90 天到期。",
        "kind": "episodic",
        "cues": ["2026-06-03", "理财"],
    },
    {
        "content": "股票账户持有 1000 股茅台，成本价 1420 元；5000 股中证500ETF，成本 7.6 元。",
        "kind": "semantic",
        "cues": ["股票", "茅台"],
    },
    {
        "content": "房贷每月 12 日还 6800 元，还剩 212 期；车贷每月 20 日还 2400 元，还剩 8 期。",
        "kind": "semantic",
        "cues": ["房贷", "车贷"],
    },
    {
        "content": "家庭保险：重疾险年缴 8600 元，9 月 15 日续费；医疗险年缴 1200 元，7 月 1 日续费。",
        "kind": "semantic",
        "cues": ["保险", "重疾险"],
    },
    {
        "content": "6月5日买了京东 5 月账单已还 3200 元，白条分期 3 期每期 500 元。",
        "kind": "episodic",
        "cues": ["2026-06-05", "京东"],
    },
    {
        "content": "5月总结：收入 20600 元，支出 14230 元，结余 6370 元，储蓄率 31%。",
        "kind": "semantic",
        "cues": ["5月总结"],
    },
    {
        "content": "订阅：视频会员每月 25 元 8 号扣款，音乐会员每月 15 元 15 号扣款，云盘 30 元/年 11 月续费。",
        "kind": "semantic",
        "cues": ["订阅", "视频会员"],
    },
    {
        "content": "家庭目标：年底前攒够 10 万应急金，目前账户合计 6.4 万。",
        "kind": "semantic",
        "cues": ["目标", "应急金"],
    },
    {
        "content": "5月28日还了朋友借款 2000 元，备注“5月借的”。",
        "kind": "episodic",
        "cues": ["2026-05-28", "借款"],
    },
    {
        "content": "6月7日退了一双鞋，退款 459 元原路退回招行卡。",
        "kind": "episodic",
        "cues": ["2026-06-07", "退款"],
    },
    {
        "content": "5月交通费实际花了 720 元，其中地铁 480 元、打车 240 元。",
        "kind": "semantic",
        "cues": ["交通"],
    },
    {
        "content": "给孩子报的游泳班年费 4800 元，6 月 1 日付的，合同号 YM-2026-061。",
        "kind": "episodic",
        "cues": ["2026-06-01", "游泳班"],
    },
    {
        "content": "发票：6月2日修车 860 元，6月3日体检 1200 元，都开了电子发票。",
        "kind": "episodic",
        "cues": ["发票", "修车"],
    },
    {
        "content": "6月4日转账给爸妈 3000 元，从招行卡出。",
        "kind": "episodic",
        "cues": ["2026-06-04", "爸妈"],
    },
    {
        "content": "5月娱乐实际花了 1350 元，超预算 350 元，原因是两次朋友聚餐。",
        "kind": "semantic",
        "cues": ["娱乐"],
    },
    {
        "content": "6月6日买机票去成都往返 1820 元，7 月 12 日出行。",
        "kind": "episodic",
        "cues": ["2026-06-06", "机票"],
    },
    {
        "content": "5月31日信用卡出账 9860 元，还款日是 6 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-05-31", "信用卡"],
    },
    {
        "content": "6月8日股票卖出 200 股茅台，成交价 1560 元，赚了 28000 元。",
        "kind": "episodic",
        "cues": ["2026-06-08", "卖出"],
    },
    {
        "content": "6月9日补缴 5 月个税 1420 元，从工资卡扣。",
        "kind": "episodic",
        "cues": ["2026-06-09", "个税"],
    },
    {
        "content": "6月10日买菜记账：超市 268 元、菜市场 96 元、外卖 74 元。",
        "kind": "episodic",
        "cues": ["2026-06-10", "买菜"],
    },
]


QUESTIONS = [
    {
        "dim": "账户信息",
        "q": "家里共用的是哪张银行卡？尾号多少？",
        "answer": "招行卡，尾号 8888",
        "terms": ["8888"],
    },
    {
        "dim": "收支记录",
        "q": "上个月的工资是多少？几号到账？",
        "answer": "18500 元，5 月 10 日",
        "terms": ["18500", "10"],
    },
    {
        "dim": "预算",
        "q": "吃饭的月预算是多少？交通呢？",
        "answer": "吃饭 3000，交通 800",
        "terms": ["3000", "800"],
    },
    {
        "dim": "投资持仓",
        "q": "股票账户里茅台和中证500ETF各持多少股？",
        "answer": "茅台 1000 股，中证500ETF 5000 股",
        "terms": ["1000", "5000"],
    },
    {
        "dim": "贷款还款",
        "q": "房贷每月还多少？还剩多少期？",
        "answer": "6800 元，剩 212 期",
        "terms": ["6800", "212"],
    },
    {
        "dim": "保险",
        "q": "重疾险什么时候续费？一年多少钱？",
        "answer": "9 月 15 日，8600 元",
        "terms": ["8600", "15"],
    },
    {
        "dim": "票据凭证",
        "q": "最近修车花了多少钱？有发票吗？",
        "answer": "860 元，有电子发票",
        "terms": ["860", "发票"],
    },
    {
        "dim": "月度总结",
        "q": "上个月结余多少？储蓄率多少？",
        "answer": "结余 6370，储蓄率 31%",
        "terms": ["6370", "31"],
    },
    {
        "dim": "订阅扣费",
        "q": "视频会员每月几号扣款？多少钱？",
        "answer": "8 号，25 元",
        "terms": ["25", "8"],
    },
    {
        "dim": "家庭目标",
        "q": "年底前的家庭目标是什么？现在还差多少？",
        "answer": "攒 10 万应急金，还差 3.6 万",
        "terms": ["10", "6.4"],
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

    db_path = os.path.join(_WORK, "finance_mem0db")
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
                "collection_name": "finance_spot",
                "path": db_path,
                "on_disk": True,
                "embedding_model_dims": 1024,
            },
        },
        "history_db_path": os.path.join(_WORK, "finance_mem0_history.db"),
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
        "domain": "个人理财",
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
    path = os.path.join(_WORK, "finance_spot.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
