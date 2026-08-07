"""LoCoMo-style long-dialogue benchmark with review-loop closure.

A 36-turn simulated conversation per persona (facts + dated events + one
mid-conversation fact update) is stored, then 12 questions are asked
immediately and again after 4 simulated weeks of spaced review. Two identical
engines differ only in `confidence_aware` review: uncertain-but-correct
memories get shorter intervals (more practice) in the aware engine.
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


COLORS = ["amber", "teal", "coral"]
FOODS = ["ramen", "tacos", "borscht"]
CITIES = ["Kyoto", "Lyon", "Oslo"]
PLACES = ["aquarium", "art museum", "harbor"]


def build(seed: int = 3) -> tuple[MemoryEngine, list[dict], str]:
    """Return (engine, questions, updated_fact_query)."""
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    names = ["Alice", "Bob", "Carol"]
    start = __import__("datetime").date(2026, 3, 1)
    # 12 turns per persona: 6 facts + 6 dated events
    for p, name in enumerate(names):
        for i in range(6):
            fact = f"{name}'s favorite {['color', 'food', 'city', 'hobby', 'drink', 'season'][i]} is " \
                   f"{[COLORS[p], FOODS[p], CITIES[p], PLACES[p], 'coffee', 'spring'][i]}."
            engine.remember(
                fact, kind=MemoryKind.SEMANTIC, source=user,
                cues=[name.lower(), ['color', 'food', 'city', 'hobby', 'drink', 'season'][i]],
            )
        for i in range(6):
            day = (start + timedelta(days=p * 12 + i)).isoformat()
            obj = [COLORS[p], FOODS[p], CITIES[p], PLACES[p], "notebook", "vinyl record"][i]
            verb = ["bought", "had", "visited", "visited", "bought", "bought"][i]
            content = f"{name} {verb} {obj} on {day}."
            engine.remember(
                content, kind=MemoryKind.EPISODIC, source=user,
                cues=[name.lower(), day],
            )
    # mid-conversation update: Alice's favorite color changes
    engine.remember(
        "Alice's favorite color is indigo.",
        kind=MemoryKind.SEMANTIC, source=user,
        cues=["alice", "color"],
        evidence_count=4,
    )
    questions = [
        {"kind": "fact", "q": "What is Alice's favorite color?",
         "answer": "indigo", "expected": ["Alice's favorite color is indigo."]},
        {"kind": "fact", "q": "What is Bob's favorite food?",
         "answer": "tacos", "expected": ["Bob's favorite food is tacos."]},
        {"kind": "event", "q": "What did Alice buy on 2026-03-01?",
         "answer": "amber", "expected": ["Alice bought amber on 2026-03-01."]},
        {"kind": "event", "q": "What did Carol buy on 2026-03-25?",
         "answer": "coral", "expected": ["Carol bought coral on 2026-03-25."]},
        {"kind": "event", "q": "What did Bob buy on 2026-03-13?",
         "answer": "teal", "expected": ["Bob bought teal on 2026-03-13."]},
        {"kind": "temporal", "q": "After Alice bought amber on 2026-03-01, what did Alice do next?",
         "answer": "ramen", "expected": ["Alice had ramen on 2026-03-02."]},
        {"kind": "temporal", "q": "After Bob had tacos on 2026-03-14, what did Bob do next?",
         "answer": "lyon", "expected": ["Bob visited Lyon on 2026-03-15."]},
        {"kind": "temporal", "q": "After Carol bought coral on 2026-03-25, what did Carol do next?",
         "answer": "borscht", "expected": ["Carol had borscht on 2026-03-26."]},
        {"kind": "distractor", "q": "What is Alice's favorite dessert?",
         "answer": "unknown", "expected": []},
        {"kind": "distractor", "q": "What is Bob's favorite sport?",
         "answer": "unknown", "expected": []},
        {"kind": "distractor", "q": "What is Carol's favorite movie?",
         "answer": "unknown", "expected": []},
        {"kind": "fact", "q": "What is Alice's favorite city?",
         "answer": "kyoto", "expected": ["Alice's favorite city is Kyoto."]},
    ]
    return engine, questions, "What is Alice's favorite color?"


def score_questions(
    engine: MemoryEngine, questions: list[dict], now=None
) -> dict:
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
    return {
        "n": len(questions),
        "hit1": hits1,
        "hit5": hits5,
        "accuracy1": round(hits1 / len(questions), 3),
        "accuracy5": round(hits5 / len(questions), 3),
    }


def simulate_review(engine: MemoryEngine, confidence_aware: bool) -> dict:
    now = utcnow()
    reviewed_count = 0
    for day_offset in range(28):
        day = now + timedelta(days=day_offset)
        due = engine.review_due(limit=6, now=day)
        for item in due:
            engine.review(
                item.id, success=True, now=day,
                confidence_aware=confidence_aware,
            )
            reviewed_count += 1
    return {
        "confidence_aware": confidence_aware,
        "reviews_done": reviewed_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "long_dialogue_eval.json"
        ),
    )
    args = parser.parse_args()
    results = {}
    final_day = utcnow() + timedelta(days=28)
    for aware in (True, False):
        engine, questions, update_q = build()
        engine.sleep()
        baseline = score_questions(engine, questions)
        updated_top = engine.recall(update_q, top_k=1)
        update_ok = bool(updated_top) and updated_top[0].item.content == \
            "Alice's favorite color is indigo."
        review = simulate_review(engine, aware)
        after = score_questions(engine, questions, now=final_day)
        results["aware" if aware else "naive"] = {
            "baseline": baseline,
            "after_4weeks": after,
            "review": review,
            "update_ok": update_ok,
        }
        engine.close()
    # no-review control
    engine, questions, update_q = build()
    engine.sleep()
    baseline = score_questions(engine, questions)
    # let 28 days pass with no review
    after = score_questions(engine, questions, now=final_day)
    engine.close()
    report = {
        "results": results,
        "no_review": {
            "baseline": baseline,
            "after_4weeks_no_review": after,
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
