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


def generate() -> dict:
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
        for i in range(4):
            day = start + timedelta(days=p * 4 + i)
            day_cn = f"{day.year}年{day.month}月{day.day}日"
            if i % 2 == 0:
                obj = PLACES[(p + i) % 3]
                action = "去了"
                content = f"{name}在{day_cn}去了{obj}。"
                answer = obj
            else:
                obj = ITEMS[(p + i) % 3]
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
        # temporal: day0 -> day1 (first two events of the persona)
        e0 = events[p * 4]
        e1 = events[p * 4 + 1]
        day0 = start + timedelta(days=p * 4)
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


_ORIGINAL = types.CJK_STOPWORDS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "zh_locomo_bench.json"
        ),
    )
    args = parser.parse_args()
    dataset = generate()
    on = evaluate(dataset, True)
    off = evaluate(dataset, False)
    report = {"on": on, "off": off}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
