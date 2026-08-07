"""Chinese LoCoMo-style long-dialogue benchmark (fact update + review loop).

Same structure as the English long-dialogue eval but in Chinese, mixing zh
dates ("2026年3月1日") and ISO dates to exercise the round-11/14 date
normalization, with a mid-dialogue fact update and a 4-week review loop.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


NAMES = ["阿丽", "小波", "小王"]
COLORS = ["琥珀色", "天蓝色", "珊瑚色"]
FOODS = ["拉面", "饺子", "火锅"]
CITIES = ["成都", "杭州", "西安"]
PLACES = ["植物园", "水族馆", "老城区"]
ITEMS = ["笔记本", "相机", "咖啡豆"]


def _zh_date(day) -> str:
    return f"{day.year}年{day.month}月{day.day}日"


def build(sessions: int = 6) -> tuple[MemoryEngine, list[dict], str]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    from datetime import date

    start = date(2026, 3, 1)
    for p, name in enumerate(NAMES):
        for key, value in (
            ("颜色", COLORS[p]), ("食物", FOODS[p]), ("城市", CITIES[p]),
            ("爱好", PLACES[p]), ("饮料", "咖啡"), ("季节", "春天"),
        ):
            engine.remember(
                f"{name}最喜欢的{key}是{value}。",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[name, key],
            )
        for i in range(sessions):
            day = start + timedelta(days=p * sessions + i)
            day_str = _zh_date(day) if i % 2 == 0 else day.isoformat()
            cycle = [
                COLORS[p], FOODS[p], CITIES[p], PLACES[p],
                "笔记本", "唱片",
            ]
            verbs = ["买了", "吃了", "去了", "去了", "买了", "买了"]
            obj = f"{cycle[i % 6]}{i // 6 or ''}"
            verb = verbs[i % 6]
            engine.remember(
                f"{name}在{day_str}{verb}{obj}。",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=[name, day.isoformat()],
            )
    # mid-dialogue update: Alice's favorite color changes
    engine.remember(
        "阿丽最喜欢的颜色是靛蓝色。",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["阿丽", "颜色"],
        evidence_count=4,
    )
    questions = [
        {"kind": "fact", "q": "阿丽最喜欢的颜色是什么？",
         "answer": "靛蓝色", "expected": ["阿丽最喜欢的颜色是靛蓝色。"]},
        {"kind": "fact", "q": "小波最喜欢的食物是什么？",
         "answer": "饺子", "expected": ["小波最喜欢的食物是饺子。"]},
        {"kind": "event", "q": "阿丽在2026-03-01买了什么？",
         "answer": "琥珀色", "expected": ["阿丽在2026年3月1日买了琥珀色。"]},
        {"kind": "event", "q": "小王在2026年3月25日买了什么？",
         "answer": "珊瑚色", "expected": ["小王在2026年3月25日买了珊瑚色。"]},
        {"kind": "event", "q": "小波在2026年3月14日吃了什么？",
         "answer": "饺子", "expected": ["小波在2026-03-14吃了饺子。"]},
        {"kind": "temporal", "q": "阿丽在2026年3月1日买了琥珀色之后，接下来做了什么？",
         "answer": "拉面", "expected": ["阿丽在2026-03-02吃了拉面。"]},
        {"kind": "temporal", "q": "小波在2026年3月13日买了天蓝色之后，接下来做了什么？",
         "answer": "饺子", "expected": ["小波在2026-03-14吃了饺子。"]},
        {"kind": "temporal", "q": "小王在2026年3月25日买了珊瑚色之后，接下来做了什么？",
         "answer": "火锅", "expected": ["小王在2026-03-26吃了火锅。"]},
        {"kind": "distractor", "q": "阿丽最喜欢的甜点是什么？",
         "answer": "unknown", "expected": []},
        {"kind": "distractor", "q": "小波最喜欢的运动是什么？",
         "answer": "unknown", "expected": []},
        {"kind": "distractor", "q": "小王最喜欢的电影是什么？",
         "answer": "unknown", "expected": []},
        {"kind": "fact", "q": "阿丽最喜欢的城市是什么？",
         "answer": "成都", "expected": ["阿丽最喜欢的城市是成都。"]},
    ]
    return engine, questions, "阿丽最喜欢的颜色是什么？"


def score_questions(engine, questions, now=None) -> dict:
    hits5 = hits1 = 0
    for q in questions:
        if q["kind"] == "distractor":
            hits1 += 1
            hits5 += 1
            continue
        results = engine.recall(q["q"], top_k=5, now=now)
        contents = [r.item.content for r in results]
        if results and contents[0] == q["expected"][0]:
            hits1 += 1
        if all(e in contents for e in q["expected"]):
            hits5 += 1
    return {"n": len(questions), "hit1": hits1, "hit5": hits5,
            "accuracy1": round(hits1 / len(questions), 3),
            "accuracy5": round(hits5 / len(questions), 3)}


def simulate_review(engine, confidence_aware: bool) -> int:
    now = utcnow()
    count = 0
    for day_offset in range(28):
        day = now + timedelta(days=day_offset)
        for item in engine.review_due(limit=6, now=day):
            engine.review(
                item.id, success=True, now=day,
                confidence_aware=confidence_aware,
            )
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sessions", type=int, default=6)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "zh_long_dialogue_eval.json"
        ),
    )
    args = parser.parse_args()
    final_day = utcnow() + timedelta(days=28)
    results = {}
    for aware in (True, False):
        engine, questions, update_q = build(args.sessions)
        engine.sleep()
        baseline = score_questions(engine, questions)
        update_top = engine.recall(update_q, top_k=1)
        update_ok = bool(update_top) and update_top[0].item.content == \
            "阿丽最喜欢的颜色是靛蓝色。"
        reviews = simulate_review(engine, aware)
        after = score_questions(engine, questions, now=final_day)
        results["aware" if aware else "naive"] = {
            "baseline": baseline, "after_4weeks": after,
            "reviews": reviews, "update_ok": update_ok,
        }
        engine.close()
    engine, questions, _ = build(args.sessions)
    engine.sleep()
    no_review = score_questions(engine, questions, now=final_day)
    engine.close()
    report = {"sessions": args.sessions, "results": results,
              "no_review": no_review}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
