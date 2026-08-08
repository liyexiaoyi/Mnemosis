"""Health-records spot-check (round 260): Mnemosis vs mem0 official ONLY.

New domain (健康/医疗记录) with deliberate temporal interference:
multiple blood-pressure and glucose records; questions ask "上次/最近"
so the correct memory is the MOST RECENT one, not just any matching one.
10 new dimensions:

  体检记录 / 血压监测 / 用药记录 / 复诊安排 / 化验指标 /
  疫苗记录 / 过敏史 / 医生建议 / 医保费用 / 家族病史
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
        "content": "2026年5月20日年度体检：身高 172cm，体重 71kg，BMI 24，结论：轻度脂肪肝，建议减重。",
        "kind": "episodic",
        "cues": ["2026-05-20", "体检"],
    },
    {
        "content": "2025年体检结论：各项正常，仅维生素 D 偏低。",
        "kind": "episodic",
        "cues": ["2025", "体检"],
    },
    {
        "content": "2026年6月1日血压 128/82。",
        "kind": "episodic",
        "cues": ["2026-06-01", "血压"],
    },
    {
        "content": "2026年6月20日血压 135/86。",
        "kind": "episodic",
        "cues": ["2026-06-20", "血压"],
    },
    {
        "content": "2026年7月5日血压 122/78，正常。",
        "kind": "episodic",
        "cues": ["2026-07-05", "血压"],
    },
    {
        "content": "现在每天吃氨氯地平 5mg，早上 8 点吃，已连续 3 个月。",
        "kind": "semantic",
        "cues": ["氨氯地平", "用药"],
    },
    {
        "content": "阿司匹林 100mg 隔天一次，用于预防心梗。",
        "kind": "semantic",
        "cues": ["阿司匹林", "用药"],
    },
    {
        "content": "感冒时吃布洛芬，一次 1 粒，一天最多 3 次。",
        "kind": "semantic",
        "cues": ["布洛芬", "用药"],
    },
    {
        "content": "下次复查安排在 8 月 15 日，找王医生。",
        "kind": "semantic",
        "cues": ["复查", "王医生"],
    },
    {
        "content": "2026年6月25日空腹血糖 6.2 mmol/L。",
        "kind": "episodic",
        "cues": ["2026-06-25", "血糖"],
    },
    {
        "content": "2026年7月12日空腹血糖 5.7 mmol/L，正常。",
        "kind": "episodic",
        "cues": ["2026-07-12", "血糖"],
    },
    {
        "content": "2026年5月10日糖化血红蛋白 6.4%。",
        "kind": "episodic",
        "cues": ["2026-05-10", "糖化"],
    },
    {
        "content": "2025年10月接种流感疫苗；2026年3月接种新冠加强针。",
        "kind": "episodic",
        "cues": ["2025-10", "疫苗"],
    },
    {
        "content": "2024年打过乙肝疫苗第三针。",
        "kind": "episodic",
        "cues": ["2024", "疫苗"],
    },
    {
        "content": "对青霉素过敏，就医时一定要告知医生。",
        "kind": "semantic",
        "cues": ["青霉素", "过敏"],
    },
    {
        "content": "对芒果过敏：吃了会起疹子。",
        "kind": "semantic",
        "cues": ["芒果", "过敏"],
    },
    {
        "content": "对宠物毛发不过敏（2026年记录）。",
        "kind": "semantic",
        "cues": ["宠物", "过敏"],
    },
    {
        "content": "王医生建议：每天走 8000 步、睡前不吃东西、少喝含糖饮料。",
        "kind": "semantic",
        "cues": ["王医生", "建议"],
    },
    {
        "content": "2026 年医保个人账户余额 3620 元，门诊起付线 800 元。",
        "kind": "semantic",
        "cues": ["医保", "余额"],
    },
    {
        "content": "家族史：父亲有高血压，母亲有糖尿病史；爷爷心梗过。",
        "kind": "semantic",
        "cues": ["家族史", "父亲"],
    },
    {
        "content": "6月体重 70kg，7月 69kg，目标 67kg。",
        "kind": "episodic",
        "cues": ["体重"],
    },
    {
        "content": "最近睡眠平均 6.5 小时，医生建议 7-8 小时。",
        "kind": "semantic",
        "cues": ["睡眠"],
    },
    {
        "content": "8月3日约了肺部 CT，因为连续咳嗽两周。",
        "kind": "episodic",
        "cues": ["CT", "咳嗽"],
    },
    {
        "content": "2026年7月15日血常规：白细胞 6.8，血红蛋白 142。",
        "kind": "episodic",
        "cues": ["2026-07-15", "血常规"],
    },
    {
        "content": "7月门诊花费 260 元，其中挂号 20 元，检查 240 元。",
        "kind": "episodic",
        "cues": ["门诊", "花费"],
    },
    {
        "content": "2026年7月18日转诊到内分泌科，看血糖问题。",
        "kind": "episodic",
        "cues": ["2026-07-18", "转诊"],
    },
]


QUESTIONS = [
    {
        "dim": "体检记录",
        "q": "最近一次年度体检的结论是什么？",
        "answer": "轻度脂肪肝，建议减重",
        "terms": ["脂肪肝"],
    },
    {
        "dim": "血压监测",
        "q": "上次量血压是多少？",
        "answer": "122/78",
        "terms": ["122", "78"],
    },
    {
        "dim": "用药记录",
        "q": "现在每天吃的降压药是什么？剂量多少？",
        "answer": "氨氯地平 5mg",
        "terms": ["氨氯地平", "5mg"],
    },
    {
        "dim": "复诊安排",
        "q": "下次复查安排在什么时候？找哪位医生？",
        "answer": "8 月 15 日，王医生",
        "terms": ["15", "王医生"],
    },
    {
        "dim": "化验指标",
        "q": "最近一次空腹血糖是多少？",
        "answer": "5.7 mmol/L",
        "terms": ["5.7"],
    },
    {
        "dim": "疫苗记录",
        "q": "最近一次接种流感疫苗是什么时候？",
        "answer": "2025年10月",
        "terms": ["流感疫苗"],
    },
    {
        "dim": "过敏史",
        "q": "对什么药物过敏？",
        "answer": "青霉素",
        "terms": ["青霉素"],
    },
    {
        "dim": "医生建议",
        "q": "医生建议每天走多少步？",
        "answer": "8000 步",
        "terms": ["8000"],
    },
    {
        "dim": "医保费用",
        "q": "今年医保个人账户余额多少？",
        "answer": "3620 元",
        "terms": ["3620"],
    },
    {
        "dim": "家族病史",
        "q": "父亲有什么病史？",
        "answer": "高血压",
        "terms": ["高血压"],
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

    db_path = os.path.join(_WORK, "health_mem0db")
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
                "collection_name": "health_spot",
                "path": db_path,
                "on_disk": True,
                "embedding_model_dims": 1024,
            },
        },
        "history_db_path": os.path.join(_WORK, "health_mem0_history.db"),
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
        "domain": "健康医疗",
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
    path = os.path.join(_WORK, "health_spot.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
