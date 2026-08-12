"""Bulk long-text memory bench: Mnemosis vs mem0 at large volume.

Feeds hundreds of long Chinese records (200-400 chars each) into both
systems, then asks 10 questions whose answers are buried inside long noisy
records. Measures retrieval hit@5, cloud answers and local small-model
answers on the exact retrieved contexts.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import shutil
import sys
import time
import urllib.request

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
_WORK = os.path.normpath(os.path.join(_BENCH, "..", "..", "work"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from game_dev_spot_bench import cloud_generate

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

VISION_CONFIG = r"C:\Users\asus\plugins\image-viewer\scripts\vision_config.json"
OLLAMA_URL = "http://127.0.0.1:11434"


TARGETS = [
    ("客户的宠物狗叫什么名字？", "客户的宠物狗叫豆豆", ["豆豆"]),
    ("服务器的备份时间定在几点？", "服务器的备份时间定在凌晨2点", ["2点"]),
    ("单笔报销上限是多少？", "单笔报销上限是800元", ["800"]),
    ("合同评审用哪个会议室？", "合同评审使用A-307会议室", ["307"]),
    ("系统密码的提示是什么？", "系统密码提示是桂花糕", ["桂花糕"]),
    ("备用供应商的电话是多少？", "备用供应商的电话是139-5555-1234", ["5555"]),
    ("新版本计划什么时候上线？", "新版本计划6月18日上线", ["18"]),
    ("仓库里库存多少台设备？", "仓库库存137台设备", ["137"]),
    ("项目对接人的邮箱是什么？", "项目对接人邮箱是ly@example.com", ["example"]),
    ("第二期合同金额是多少？", "第二期合同金额68000元", ["68000"]),
]


def _target_record(index: int, sentence: str) -> str:
    names = ["陈工", "李经理", "王总", "赵主管", "刘会计"]
    topics = ["数据中台", "客户画像", "权限体系", "监控告警", "接口网关"]
    name = names[index % len(names)]
    topic = topics[index % len(topics)]
    return (
        f"2026年{3 + index % 9}月{5 + index % 20}日会议纪要：由{name}主持，讨论了{topic}的"
        f"推进情况。会上一共提出了{7 + index % 6}条待办，其中3条和文档、2条和联调有关。"
        f"中途插入了大量背景说明：上个季度{topic}整体延期了约两周，原因是依赖方接口"
        f"迟迟没有返回，大家反复对齐了字段定义和超时策略，还临时调整了排期，把验收挪到了"
        f"月末。关键结论如下：{sentence}。散会前又补充讨论了数据清理、权限复核和下周的"
        f"演示安排，演示预计{40 + index % 30}分钟，由{name}主讲，测试环境提前一天准备。"
    )


def _filler_record(index: int) -> str:
    projects = ["星海", "磐石", "云图", "澜舟", "青柠"]
    people = ["张伟", "刘洋", "陈静", "王芳", "赵磊", "孙倩"]
    cities = ["上海", "北京", "深圳", "杭州", "成都"]
    project = projects[index % len(projects)]
    person = people[index % len(people)]
    city = cities[index % len(cities)]
    amount = 1000 + index * 137 % 90000
    return (
        f"项目“{project}”第{index + 1}期周报：本周在{city}完成了一次现场巡检，"
        f"参与人员包括{person}和另外{2 + index % 5}位同事。巡检主要检查了机柜温度、"
        f"网络抖动和备份完整性，发现两处隐患并已登记。预算方面本周支出约{amount}元，"
        f"主要用于设备租赁和差旅，累计执行率{60 + index % 35}%。下周计划完成版本合并、"
        f"压测和演示材料整理，同时安排一次与用户的回访，重点确认新增需求的优先级。"
        f"会议记录已归档，编号BK-{1000 + index}，如需要可随时调阅。"
    )


def generate_dataset(seed: int, count: int) -> dict:
    rng = random.Random(seed)
    records = []
    for index, (_, sentence, _) in enumerate(TARGETS):
        records.append(_target_record(index, sentence))
    while len(records) < count:
        records.append(_filler_record(len(records)))
    rng.shuffle(records)
    return {"records": records}


def _mnemosis_contexts(records, questions, top_k):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    start = time.perf_counter()
    for content in records:
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=user,
            importance=0.5,
        )
    ingest = time.perf_counter() - start
    contexts = {}
    for question in questions:
        results = engine.recall(question["q"], top_k=top_k)
        contexts[question["q"]] = [r.item.content for r in results]
    return contexts, ingest


def _mem0_contexts(records, questions, db_name, top_k):
    os.environ["MEM0_TELEMETRY"] = "False"
    with open(VISION_CONFIG, encoding="utf-8") as handle:
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
    start = time.perf_counter()
    for content in records:
        memory.add(content, user_id="u1", infer=False)
    ingest = time.perf_counter() - start
    contexts = {}
    for question in questions:
        resp = memory.search(question["q"], filters={"user_id": "u1"}, top_k=top_k)
        results = resp.get("results", [])
        contexts[question["q"]] = [
            r.get("memory", "") if isinstance(r, dict) else str(r)
            for r in results
        ]
    return contexts, ingest


def _local_generate(model: str, prompt: str) -> str:
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        OLLAMA_URL + "/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=600) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data.get("response", "").strip()


def _answer_prompt(rows, question):
    return (
        "只根据下面的记忆回答，不要编造。如果记忆里没有答案，就回答：不知道。\n\n"
        "记忆：\n"
        + "\n".join(f"- {text}" for text in rows)
        + f"\n\n问题：{question}"
    )


def _score(answers, questions):
    total = 0
    per_dim = {}
    for q in questions:
        ok = hit_text([answers[q["q"]]], q)
        total += 1 if ok else 0
        per_dim.setdefault(q["dim"], []).append(1 if ok else 0)
    return {
        "total": total,
        "per_dim": {d: round(sum(v) / len(v), 3) for d, v in per_dim.items()},
    }


def hit_text(texts: list[str], question: dict) -> bool:
    joined = " ".join(texts)
    if question["sentence"] in joined:
        return True
    return all(
        any(term in text for text in texts) for term in question["terms"]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=600, help="total long records")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--skip-cloud", action="store_true")
    parser.add_argument("--skip-local", action="store_true")
    parser.add_argument("--skip-mem0", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_WORK, "bulk_longtext_bench.json"),
    )
    args = parser.parse_args()

    dataset = generate_dataset(args.seed, args.count)
    questions = [
        {
            "dim": f"长文-{index + 1}",
            "q": q,
            "sentence": sentence,
            "terms": terms,
        }
        for index, (q, sentence, terms) in enumerate(TARGETS)
    ]
    records = dataset["records"]
    print(f"records: {len(records)} | questions: {len(questions)}", flush=True)

    contexts = {}
    ingest = {}
    contexts["mnemosis"], ingest["mnemosis"] = _mnemosis_contexts(
        records, questions, args.top_k
    )
    print(f"mnemosis ingest: {ingest['mnemosis']:.1f}s", flush=True)
    if not args.skip_mem0:
        contexts["mem0"], ingest["mem0"] = _mem0_contexts(
            records, questions, "bulk_mem0db", args.top_k
        )
        print(f"mem0 ingest: {ingest['mem0']:.1f}s", flush=True)

    retrieval = {}
    for project, rows in contexts.items():
        total = 0
        per_dim: dict[str, list[int]] = {}
        for q in questions:
            ok = hit_text(rows[q["q"]], q)
            total += int(ok)
            per_dim.setdefault(q["dim"], []).append(int(ok))
        retrieval[project] = {
            "total": total,
            "per_dim": {d: round(sum(v) / len(v), 3) for d, v in per_dim.items()},
        }
        print("retrieval", project, retrieval[project]["total"], flush=True)

    out = {
        "domain": "大文本量-长记录",
        "records": len(records),
        "top_k": args.top_k,
        "questions": questions,
        "contexts": contexts,
        "ingest_seconds": ingest,
        "retrieval": retrieval,
    }
    if not args.skip_cloud:
        answers = {}
        for project, rows in contexts.items():
            answers[project] = {}
            for q in questions:
                prompt = _answer_prompt(rows[q["q"]], q["q"])
                try:
                    answers[project][q["q"]] = cloud_generate(prompt, max_tokens=200)
                except Exception as exc:  # noqa: BLE001
                    answers[project][q["q"]] = f"<error: {exc}>"
                print(f"  cloud [{project}] {q['q'][:16]} done", flush=True)
        out["answers_cloud"] = answers
        out["accuracy_cloud"] = {
            p: _score(rows, questions) for p, rows in answers.items()
        }
        for p, acc in out["accuracy_cloud"].items():
            print("accuracy_cloud", p, acc["total"], flush=True)

    if not args.skip_local:
        local = {}
        for model in ("qwen2.5:3b", "gemma3:12b"):
            answers = {}
            for project, rows in contexts.items():
                answers[project] = {}
                for q in questions:
                    prompt = _answer_prompt(rows[q["q"]], q["q"])
                    try:
                        answers[project][q["q"]] = _local_generate(model, prompt)
                    except Exception as exc:  # noqa: BLE001
                        answers[project][q["q"]] = f"<error: {exc}>"
                    print(f"  local [{model}][{project}] {q['q'][:16]} done", flush=True)
            accuracy = {p: _score(rows, questions) for p, rows in answers.items()}
            for p, acc in accuracy.items():
                print("accuracy_local", model, p, acc["total"], flush=True)
            local[model] = {"answers": answers, "accuracy": accuracy}
        out["local"] = local

    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(out, handle, ensure_ascii=False, indent=2)
    print("saved:", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
