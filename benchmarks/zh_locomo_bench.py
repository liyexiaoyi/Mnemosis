"""Chinese (zh) LoCoMo-style benchmark.

Same structure as the English benchmark but in Chinese, with natural query
noise ("请问……是什么？"). A/B: Chinese stopword filtering on vs off (the
tokenizer reads the global CJK_STOPWORDS at call time, so we swap it).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis import types  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


NAMES = ["阿丽", "小波", "小王"]
COLORS = ["琥珀色", "天蓝色", "珊瑚色"]
FOODS = ["拉面", "饺子", "火锅"]
CITIES = ["成都", "杭州", "西安"]
PLACES = ["植物园", "水族馆", "老城区"]
ITEMS = ["笔记本", "相机", "咖啡豆"]
UNUSED = ["甜点", "运动", "季节"]


def generate(sessions: int = 4) -> dict:
    facts, events, questions = [], [], []
    start = date(2026, 3, 1)
    for p, name in enumerate(NAMES):
        for key, value in (
            ("颜色", COLORS[p]), ("食物", FOODS[p]), ("城市", CITIES[p]),
        ):
            facts.append(
                {
                    "content": f"{name}最喜欢的{key}是{value}。",
                    "kind": "semantic",
                    "cues": [name, key],
                }
            )
            questions.append(
                {
                    "kind": "fact",
                    "q": f"请问{name}最喜欢的{key}是什么？",
                    "answer": value,
                    "expected": [f"{name}最喜欢的{key}是{value}。"],
                }
            )
        for i in range(sessions):
            day = start + timedelta(days=p * sessions + i)
            day_cn = f"{day.year}年{day.month}月{day.day}日"
            if i % 2 == 0:
                obj = f"{PLACES[(p + i) % 3]}{i // 3 or ''}"
                action = "去了"
                content = f"{name}在{day_cn}去了{obj}。"
                answer = obj
            else:
                obj = f"{ITEMS[(p + i) % 3]}{i // 3 or ''}"
                action = "买了"
                content = f"{name}在{day_cn}买了{obj}。"
                answer = obj
            events.append(
                {
                    "content": content,
                    "kind": "episodic",
                    "cues": [name, day.isoformat()],
                    "action": action,
                }
            )
            questions.append(
                {
                    "kind": "event",
                    "q": f"请问{name}在{day_cn}做了什么？",
                    "answer": answer,
                    "expected": [content],
                }
            )
        # temporal questions for every consecutive pair
        base = p * sessions
        for k in range(sessions - 1):
            e0 = events[base + k]
            e1 = events[base + k + 1]
            day0 = start + timedelta(days=p * sessions + k)
            day0_cn = f"{day0.year}年{day0.month}月{day0.day}日"
            e0_obj = e0["content"].split(e0["action"])[1].rstrip("。")
            questions.append(
                {
                    "kind": "temporal",
                    "q": f"{name}在{day0_cn}{e0['action']}{e0_obj}之后，"
                         f"接下来做了什么？",
                    "answer": e1["content"].split(e1["action"])[1].rstrip("。"),
                    "expected": [e0["content"], e1["content"]],
                }
            )
    for p, name in enumerate(NAMES):
        for topic in UNUSED:
            questions.append(
                {
                    "kind": "distractor",
                    "q": f"请问{name}最喜欢的{topic}是什么？",
                    "answer": "unknown",
                    "expected": [],
                }
            )
    return {"facts": facts, "events": events, "questions": questions}


def evaluate(dataset: dict, filter_stopwords: bool) -> dict:
    types.CJK_STOPWORDS = (
        _ORIGINAL if filter_stopwords else frozenset()
    )
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for m in dataset["facts"] + dataset["events"]:
        engine.remember(
            m["content"],
            kind=MemoryKind(m["kind"]),
            source=user,
            cues=m["cues"],
            importance=0.8 if m["kind"] == "semantic" else 0.5,
        )
    stats = {"fact": [0, 0], "event": [0, 0], "temporal": [0, 0],
             "distractor": [0, 0]}
    query_tokens = 0
    top5_noise = 0
    q_count = 0
    for q in dataset["questions"]:
        kind = q["kind"]
        stats[kind][1] += 1
        if kind == "distractor":
            passed = bool(engine.check(q["q"]).gaps)
            stats[kind][0] += int(passed)
            continue
        query_tokens += len(types.tokenize(q["q"]))
        q_count += 1
        results = engine.recall(q["q"], top_k=5)
        contents = [r.item.content for r in results]
        stats[kind][0] += int(
            all(e in contents for e in q["expected"])
        )
        top5_noise += sum(
            1 for c in contents if c not in q["expected"]
        )
    engine.close()
    return {
        "filter_stopwords": filter_stopwords,
        "kind_hit5": {
            k: (v[0], v[1]) for k, v in stats.items()
        },
        "total": (
            sum(v[0] for v in stats.values()),
            sum(v[1] for v in stats.values()),
        ),
        "avg_query_tokens": round(query_tokens / q_count, 2),
        "avg_top5_noise": round(top5_noise / q_count, 2),
    }


def sample_questions(questions: list[dict], max_total: int) -> list[dict]:
    """Sample evenly across kinds so large runs stay comparable in runtime."""
    if max_total <= 0 or len(questions) <= max_total:
        return questions
    chosen: list[dict] = []
    for kind in ("fact", "event", "temporal", "distractor"):
        pool = [q for q in questions if q["kind"] == kind]
        per = max(1, max_total // 4)
        chosen.extend(pool[:per])
    return chosen[:max_total]


def cross_format_pairs() -> tuple[list[dict], list[dict]]:
    """12 zh-date memories (queried by ISO date) + 12 ISO memories (queried
    by zh date)."""
    memories: list[dict] = []
    questions: list[dict] = []
    start = date(2026, 5, 1)
    for i in range(12):
        day = start + timedelta(days=i)
        iso = day.isoformat()
        zh = f"{day.year}年{day.month}月{day.day}日"
        person = NAMES[i % 3]
        obj = ITEMS[i % 3]
        if i % 2 == 0:
            memories.append(
                {
                    "content": f"{person}在{zh}买了{obj}。",
                    "kind": "episodic",
                    "cues": [person],
                }
            )
            questions.append(
                {
                    "kind": "event",
                    "q": f"{person}在{iso}买了什么？",
                    "answer": obj,
                    "expected": [f"{person}在{zh}买了{obj}。"],
                }
            )
        else:
            memories.append(
                {
                    "content": f"{person}在{iso}买了{obj}。",
                    "kind": "episodic",
                    "cues": [person],
                }
            )
            questions.append(
                {
                    "kind": "event",
                    "q": f"{person}在{zh}买了什么？",
                    "answer": obj,
                    "expected": [f"{person}在{iso}买了{obj}。"],
                }
            )
    return memories, questions


def evaluate_cross(normalize: bool) -> dict:
    types.ZH_DATE_NORMALIZE = normalize
    memories, questions = cross_format_pairs()
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for m in memories:
        engine.remember(
            m["content"],
            kind=MemoryKind(m["kind"]),
            source=user,
            cues=m["cues"],
            importance=0.5,
        )
    hits = 0
    for q in questions:
        results = engine.recall(q["q"], top_k=5)
        contents = [r.item.content for r in results]
        hits += int(all(e in contents for e in q["expected"]))
    engine.close()
    return {"normalize": normalize, "hit5": (hits, len(questions))}


ZH_NUM_MONTHS = ["一月", "二月", "三月", "四月", "五月", "六月",
                 "七月", "八月", "九月", "十月", "十一月", "十二月"]
ZH_NUM_DAYS = ["一日", "二日", "三日", "四日", "五日", "六日",
               "七日", "八日", "九日", "十日", "十一日", "十二日"]


def numeral_date_pairs() -> tuple[list[dict], list[dict]]:
    memories: list[dict] = []
    questions: list[dict] = []
    for i in range(10):
        person = NAMES[i % 3]
        obj = ITEMS[i % 3]
        zh_date = f"2026年{ZH_NUM_MONTHS[i]}{ZH_NUM_DAYS[i]}"
        iso = f"2026-{i + 1:02d}-{i + 1:02d}"
        if i % 2 == 0:
            memories.append(
                {
                    "content": f"{person}在{zh_date}买了{obj}。",
                    "kind": "episodic",
                    "cues": [person],
                }
            )
            questions.append(
                {
                    "kind": "event",
                    "q": f"{person}在{iso}买了什么？",
                    "answer": obj,
                    "expected": [f"{person}在{zh_date}买了{obj}。"],
                }
            )
        else:
            memories.append(
                {
                    "content": f"{person}在{iso}买了{obj}。",
                    "kind": "episodic",
                    "cues": [person],
                }
            )
            questions.append(
                {
                    "kind": "event",
                    "q": f"{person}在{zh_date}买了什么？",
                    "answer": obj,
                    "expected": [f"{person}在{iso}买了{obj}。"],
                }
            )
    return memories, questions


def evaluate_numeral(normalize: bool) -> dict:
    types.ZH_DATE_NORMALIZE = normalize
    memories, questions = numeral_date_pairs()
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for m in memories:
        engine.remember(
            m["content"],
            kind=MemoryKind(m["kind"]),
            source=user,
            cues=m["cues"],
            importance=0.5,
        )
    hits = 0
    for q in questions:
        results = engine.recall(q["q"], top_k=5)
        contents = [r.item.content for r in results]
        hits += int(all(e in contents for e in q["expected"]))
    engine.close()
    return {"normalize": normalize, "hit5": (hits, len(questions))}


_ORIGINAL = types.CJK_STOPWORDS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=4)
    parser.add_argument("--max-questions", type=int, default=0)
    parser.add_argument("--with-llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "zh_locomo_bench.json"
        ),
    )
    args = parser.parse_args()
    dataset = generate(args.sessions)
    if args.max_questions:
        dataset["questions"] = sample_questions(
            dataset["questions"], args.max_questions
        )
    on = evaluate(dataset, True)
    off = evaluate(dataset, False)
    cross_on = evaluate_cross(True)
    cross_off = evaluate_cross(False)
    numeral_on = evaluate_numeral(True)
    numeral_off = evaluate_numeral(False)
    report = {"sessions": args.sessions, "on": on, "off": off,
              "cross_format": {"on": cross_on, "off": cross_off},
              "numeral_dates": {"on": numeral_on, "off": numeral_off}}
    if args.with_llm:
        from compare_with_models import ollama_generate, score_answer
        engine = MemoryEngine()
        user = SourceRecord(origin=SourceType.USER)
        for m in dataset["facts"] + dataset["events"]:
            engine.remember(
                m["content"],
                kind=MemoryKind(m["kind"]),
                source=user,
                cues=m["cues"],
                importance=0.8 if m["kind"] == "semantic" else 0.5,
            )
        chosen = []
        for kind in ("fact", "event", "temporal", "distractor"):
            pool = [q for q in dataset["questions"] if q["kind"] == kind]
            chosen.extend(pool[:3])
        llm = {"bare": {"hits": 0, "n": len(chosen), "rows": []},
               "with_mnemosis": {"hits": 0, "n": len(chosen), "rows": []}}
        for q in chosen:
            for cond, prompt in (
                ("bare",
                 f"请只回答答案本身；不知道就回答“unknown”。\n问题：{q['q']}"),
                ("with_mnemosis",
                 "请只根据下面的记忆上下文回答；上下文里没有就回答“unknown”。\n\n"
                 "上下文：\n"
                 + "\n".join(
                     f"- {r.item.content}"
                     for r in engine.recall(q["q"], top_k=5)
                 )
                 + f"\n\n问题：{q['q']}"),
            ):
                answer = ollama_generate("qwen2.5:3b", prompt)
                score = score_answer(answer, q["answer"])
                llm[cond]["hits"] += int(score >= 1.0)
                llm[cond]["rows"].append(
                    {"q": q["q"], "answer": answer,
                     "expected": q["answer"], "score": round(score, 2)}
                )
        for cond in llm:
            llm[cond]["accuracy"] = round(
                llm[cond]["hits"] / llm[cond]["n"], 3
            )
        report["llm_zh"] = {
            cond: {k: v for k, v in llm[cond].items() if k != "rows"}
            for cond in llm
        }
        engine.close()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
