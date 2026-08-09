"""Bulk noise-stress memory bench: Mnemosis vs mem0 at 3000+ records.

Interference design:
  - each question has 3 near-duplicate decoy records (same topic, different
    value/date) so only the right time-cued record passes;
  - fillers deliberately mention the question keywords (宠物/备份/报销/会议室/
    密码/供应商/版本/库存/邮箱/合同/门禁/打印机) to create partial matches;
  - ~3% of records are garbled/noisy text.
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

from game_dev_spot_bench import cloud_generate  # noqa: E402
from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402

VISION_CONFIG = r"C:\Users\asus\plugins\image-viewer\scripts\vision_config.json"
OLLAMA_URL = "http://127.0.0.1:11434"


TARGETS = [
    ("客户上周登记的宠物狗叫什么名字？", "客户的宠物狗上周登记叫豆豆", ["豆豆"], ["客户的宠物狗3月登记叫旺财", "客户的宠物狗5月登记叫小白", "客户的宠物狗去年登记叫来福"]),
    ("服务器备份时间上周调成几点？", "服务器备份时间上周调整为凌晨2点", ["2点"], ["服务器备份时间3月调成凌晨1点", "服务器备份时间5月调成凌晨3点", "服务器备份时间去年调成凌晨4点"]),
    ("单笔报销上限上周提高到多少？", "单笔报销上限上周提高到800元", ["800"], ["单笔报销上限3月提高到400元", "单笔报销上限5月提高到600元", "单笔报销上限去年提高到1000元"]),
    ("上周合同评审用哪个会议室？", "合同评审上周改到A-307会议室", ["307"], ["合同评审3月改到B-201会议室", "合同评审5月改到C-105会议室", "合同评审去年改到D-408会议室"]),
    ("系统密码提示上周改成什么？", "系统密码提示上周改成桂花糕", ["桂花糕"], ["系统密码提示3月改成红豆沙", "系统密码提示5月改成绿豆汤", "系统密码提示去年改成芝麻糊"]),
    ("上周换的备用供应商电话是多少？", "备用供应商上周换成139-5555-1234", ["5555"], ["备用供应商3月换成138-1111-5678", "备用供应商5月换成137-2222-6789", "备用供应商去年换成136-3333-7890"]),
    ("新版本上周定在什么时候上线？", "新版本上周定在6月18日上线", ["18"], ["新版本3月定在7月2日上线", "新版本5月定在8月9日上线", "新版本去年定在9月15日上线"]),
    ("上周盘点的库存是多少台？", "仓库库存上周盘点为137台", ["137"], ["仓库库存3月盘点为96台", "仓库库存5月盘点为215台", "仓库库存去年盘点为328台"]),
    ("项目对接人上周换的邮箱是什么？", "项目对接人邮箱上周换成ly@example.com", ["example"], ["项目对接人邮箱3月换成aaa@test.com", "项目对接人邮箱5月换成bbb@demo.com", "项目对接人邮箱去年换成ccc@sandbox.com"]),
    ("上周确认的第二期合同金额是多少？", "第二期合同金额上周确认为68000元", ["68000"], ["第二期合同金额3月确认为32000元", "第二期合同金额5月确认为45000元", "第二期合同金额去年确认为76000元"]),
    ("办公区门禁上周更新成几点关闭？", "办公区门禁上周更新为晚10点关闭", ["10"], ["办公区门禁3月更新为晚9点关闭", "办公区门禁5月更新为晚11点关闭", "办公区门禁去年更新为晚12点关闭"]),
    ("三楼打印机上周搬到哪个区？", "三楼打印机上周搬到A区", ["A区"], ["三楼打印机3月搬到B区", "三楼打印机5月搬到C区", "三楼打印机去年搬到D区"]),
]

TOPIC_WORDS = ["宠物", "备份", "报销", "会议室", "密码", "供应商", "版本", "库存", "邮箱", "合同", "门禁", "打印机"]


def _meeting_record(index: int, sentence: str, decoy: bool = False) -> str:
    names = ["陈工", "李经理", "王总", "赵主管", "刘会计"]
    topics = ["数据中台", "客户画像", "权限体系", "监控告警", "接口网关"]
    name = names[index % len(names)]
    topic = topics[index % len(topics)]
    month = 3 + index % 9
    day = 5 + index % 20
    tag = "诱饵记录" if decoy else "目标记录"
    return (
        f"2026年{month}月{day}日会议纪要：由{name}主持，讨论了{topic}的推进情况。"
        f"会上提出{7 + index % 6}条待办，其中3条和文档、2条和联调有关。中途补充了大量背景："
        f"上个季度{topic}延期约两周，依赖方接口反复对齐字段和超时策略，排期临时调整，"
        f"验收挪到月末。另外还顺带聊到了宠物档案、备份策略、报销流程、会议室预订、"
        f"系统密码、供应商名录、版本计划、库存盘点、邮箱变更、合同金额、门禁时间、打印机位置"
        f"等杂项，但都没有形成结论。关键结论如下：{sentence}。散会前补充分配了数据清理、"
        f"权限复核和下周演示任务（{tag}）。"
    )


def _filler_record(index: int, rng: random.Random) -> str:
    projects = ["星海", "磐石", "云图", "澜舟", "青柠"]
    people = ["张伟", "刘洋", "陈静", "王芳", "赵磊", "孙倩"]
    cities = ["上海", "北京", "深圳", "杭州", "成都"]
    project = projects[index % len(projects)]
    person = people[index % len(people)]
    city = cities[index % len(cities)]
    topic = rng.choice(TOPIC_WORDS)
    amount = 1000 + index * 137 % 90000
    return (
        f"项目“{project}”第{index + 1}期周报：本周在{city}完成巡检，参与人员包括{person}"
        f"和另外{2 + index % 5}位同事。巡检涉及{topic}相关事项，检查了机柜温度、网络抖动和"
        f"备份完整性，登记了两处隐患。预算支出约{amount}元，累计执行率{60 + index % 35}%。"
        f"下周计划完成版本合并、压测和演示材料整理，同时安排用户回访确认新增需求优先级。"
        f"会议记录编号BK-{1000 + index}，可随时调阅。"
    )


def _garbled_record(index: int, rng: random.Random) -> str:
    topic = rng.choice(TOPIC_WORDS)
    return (
        f"###!! {topic} @@@ 记录 {index} ？？？ 会议 ￥￥￥ 报销 ￥ 电话 ！！！！ "
        f"asdf 乱码 12345 %%% 待办 备份 待确认 邮箱 xxx 下周再说 ！@#￥%……&"
    )


def generate_dataset(seed: int, count: int) -> dict:
    rng = random.Random(seed)
    records = []
    meta = {"targets": 0, "decoys": 0, "garbled": 0}
    for index, (_, sentence, _, decoys) in enumerate(TARGETS):
        records.append(_meeting_record(index, sentence))
        meta["targets"] += 1
        for d_index, decoy in enumerate(decoys):
            records.append(_meeting_record(index * 10 + d_index, decoy, decoy=True))
            meta["decoys"] += 1
    filler_count = count - len(records)
    for i in range(filler_count):
        if i % 33 == 0:
            records.append(_garbled_record(i, rng))
            meta["garbled"] += 1
        else:
            records.append(_filler_record(i, rng))
    rng.shuffle(records)
    return {"records": records, "meta": meta}


def _mnemosis_contexts(records, questions, top_k):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    start = time.perf_counter()
    for content in records:
        engine.remember(content, kind=MemoryKind.EPISODIC, source=user, importance=0.5)
    ingest = time.perf_counter() - start
    contexts = {
        q["q"]: [r.item.content for r in engine.recall(q["q"], top_k=top_k)]
        for q in questions
    }
    return contexts, ingest


def _mem0_contexts(records, questions, db_name, top_k):
    os.environ["MEM0_TELEMETRY"] = "False"
    cfg = json.load(open(VISION_CONFIG, encoding="utf-8"))
    from mem0 import Memory

    db_path = os.path.join(_WORK, db_name)
    if os.path.isdir(db_path):
        shutil.rmtree(db_path)
    config = {
        "llm": {"provider": "openai", "config": {"model": cfg["model"], "api_key": cfg["api_key"], "openai_base_url": cfg["base_url"], "temperature": 0}},
        "embedder": {"provider": "openai", "config": {"model": "text-embedding-v3", "api_key": cfg["api_key"], "openai_base_url": cfg["base_url"]}},
        "vector_store": {"provider": "qdrant", "config": {"collection_name": db_name, "path": db_path, "on_disk": True, "embedding_model_dims": 1024}},
        "history_db_path": os.path.join(_WORK, db_name + "_history.db"),
    }
    memory = Memory.from_config(config)
    start = time.perf_counter()
    for content in records:
        memory.add(content, user_id="u1", infer=False)
    ingest = time.perf_counter() - start
    contexts = {}
    for q in questions:
        resp = memory.search(q["q"], filters={"user_id": "u1"}, top_k=top_k)
        results = resp.get("results", [])
        contexts[q["q"]] = [r.get("memory", "") if isinstance(r, dict) else str(r) for r in results]
    return contexts, ingest


def hit_text(texts: list[str], question: dict) -> bool:
    joined = " ".join(texts)
    return question["sentence"] in joined or all(
        any(term in text for text in texts) for term in question["terms"]
    )


def _score(answers, questions):
    total = 0
    per_dim = {}
    for q in questions:
        ok = hit_text([answers[q["q"]]], q)
        total += int(ok)
        per_dim.setdefault(q["dim"], []).append(int(ok))
    return {"total": total, "per_dim": {d: round(sum(v) / len(v), 3) for d, v in per_dim.items()}}


def _local_generate(model: str, prompt: str) -> str:
    payload = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"temperature": 0}}).encode("utf-8")
    req = urllib.request.Request(OLLAMA_URL + "/api/generate", data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8")).get("response", "").strip()


def _answer_prompt(rows, question):
    return (
        "只根据下面的记忆回答，不要编造。如果记忆里没有答案，就回答：不知道。\n\n"
        "记忆：\n" + "\n".join(f"- {text}" for text in rows) + f"\n\n问题：{question}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--count", type=int, default=3000)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--skip-cloud", action="store_true")
    parser.add_argument("--skip-local", action="store_true")
    parser.add_argument("--skip-mem0", action="store_true")
    parser.add_argument("--out", default=os.path.join(_WORK, "bulk_noise_bench.json"))
    args = parser.parse_args()

    dataset = generate_dataset(args.seed, args.count)
    questions = [
        {"dim": f"噪声-{index + 1}", "q": q, "sentence": sentence, "terms": terms}
        for index, (q, sentence, terms, _) in enumerate(TARGETS)
    ]
    records = dataset["records"]
    print("records:", len(records), "| meta:", dataset["meta"], flush=True)

    contexts = {}
    ingest = {}
    contexts["mnemosis"], ingest["mnemosis"] = _mnemosis_contexts(records, questions, args.top_k)
    print(f"mnemosis ingest: {ingest['mnemosis']:.1f}s", flush=True)
    if not args.skip_mem0:
        contexts["mem0"], ingest["mem0"] = _mem0_contexts(records, questions, "noise_mem0db", args.top_k)
        print(f"mem0 ingest: {ingest['mem0']:.1f}s", flush=True)

    retrieval = {}
    for project, rows in contexts.items():
        total = 0
        per_dim: dict[str, list[int]] = {}
        for q in questions:
            ok = hit_text(rows[q["q"]], q)
            total += int(ok)
            per_dim.setdefault(q["dim"], []).append(int(ok))
        retrieval[project] = {"total": total, "per_dim": {d: round(sum(v) / len(v), 3) for d, v in per_dim.items()}}
        print("retrieval", project, retrieval[project]["total"], flush=True)

    out = {
        "domain": "大文本量-高干扰",
        "records": len(records),
        "meta": dataset["meta"],
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
                try:
                    answers[project][q["q"]] = cloud_generate(_answer_prompt(rows[q["q"]], q["q"]), max_tokens=200)
                except Exception as exc:  # noqa: BLE001
                    answers[project][q["q"]] = f"<error: {exc}>"
                print(f"  cloud [{project}] {q['q'][:16]} done", flush=True)
        out["answers_cloud"] = answers
        out["accuracy_cloud"] = {p: _score(rows, questions) for p, rows in answers.items()}
        for p, acc in out["accuracy_cloud"].items():
            print("accuracy_cloud", p, acc["total"], flush=True)

    if not args.skip_local:
        local = {}
        for model in ("qwen2.5:3b", "gemma3:12b"):
            answers = {}
            for project, rows in contexts.items():
                answers[project] = {}
                for q in questions:
                    try:
                        answers[project][q["q"]] = _local_generate(model, _answer_prompt(rows[q["q"]], q["q"]))
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
