"""Reasoning mini-benchmark for time-cell temporal reasoning (round 25).

Small, deterministic chains of dated events per person. Question kinds:

  - after1     : "after X on D, what did P do next?"  (nearest future event)
  - after2     : "two events after X on D ..."       (transitive two-hop)
  - before1    : "before X on D, what did P do?"     (nearest past event)
  - event      : "what did P do on D?"               (exact-date control)
  - cross_person: anchor of one person, ask about another (scoping control)

Runs the same questions with time-cell reasoning on and off so the A/B is
directly comparable.
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
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


PEOPLE = ["alice", "bob", "lina", "mia", "kai", "nina"]
VERBS = ["bought", "visited", "had for dinner"]
# one unique object per (person, slot) so targets never share content words
# with each other's or the anchor's question - only the person cue and the
# time-cell mechanism can connect them.
OBJECTS = {
    "alice": ["a notebook", "the aquarium", "ramen", "a camera",
              "the art museum", "tacos", "hiking boots", "the garden"],
    "bob": ["a pen", "the harbor", "pizza", "a phone",
            "the zoo", "sushi", "a lamp", "the park"],
    "lina": ["a book", "the cinema", "noodles", "a hat",
             "the beach", "dumplings", "a scarf", "the mall"],
    "mia": ["a plant", "the bakery", "salad", "a ring",
            "the cafe", "berries", "a chair", "the tower"],
    "kai": ["paper", "the gym", "soup", "a watch",
            "the river", "toast", "a mat", "the castle"],
    "nina": ["a pencil", "the market", "curry", "a glass",
             "the farm", "cake", "a bag", "the hill"],
}


def build() -> tuple[MemoryEngine, list[dict]]:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    events: dict[str, list[dict]] = {}
    start = date(2026, 4, 1)
    for p, person in enumerate(PEOPLE):
        chain = []
        for i, obj in enumerate(OBJECTS[person]):
            day = start + timedelta(days=p * 10 + i)
            verb = VERBS[i % 3]
            if verb == "had for dinner":
                action = f"had {obj} for dinner"
            else:
                action = f"{verb} {obj}"
            content = f"{person} {action} on {day.isoformat()}."
            engine.remember(
                content,
                kind=MemoryKind.EPISODIC,
                source=source,
                cues=[person, day.isoformat()],
                importance=0.5,
            )
            chain.append({"content": content, "person": person,
                          "date": day.isoformat(), "action": action,
                          "object": obj})
        events[person] = chain

    questions: list[dict] = []
    for person in PEOPLE:
        chain = events[person]
        # after1: anchor day i, answer = i+1
        for i in (0, 2, 4):
            questions.append(_q(
                "after1", person, chain[i], chain[i + 1],
                f"After {person} {chain[i]['action']} on {chain[i]['date']}, "
                f"what did {person} do next?",
            ))
        # after2: transitive two-hop, answer = i+2
        for i in (0, 3):
            questions.append(_q(
                "after2", person, chain[i], chain[i + 2],
                f"Two events after {person} {chain[i]['action']} on "
                f"{chain[i]['date']}, what did {person} do?",
            ))
        # before1: anchor day i, answer = i-1
        for i in (3, 6):
            questions.append(_q(
                "before1", person, chain[i], chain[i - 1],
                f"Before {person} {chain[i]['action']} on {chain[i]['date']}, "
                f"what did {person} do?",
            ))
        # event control: exact date
        questions.append(_q(
            "event", person, chain[2], chain[2],
            f"What did {person} do on {chain[2]['date']}?",
        ))
    # cross-person scoping: ask about bob after an alice anchor; the correct
    # answer is bob's own next event (bob's anchor day 1 -> day 2).
    a0 = events["alice"][0]
    # bob's earliest event after alice's anchor date (bob day0 = 04-11)
    b0 = events["bob"][0]
    questions.append(_q(
        "cross_person", "bob", a0, b0,
        f"After {a0['person']} {a0['action']} on {a0['date']}, "
        f"what did bob do next?",
        anchor_expected=a0["content"],
    ))
    a3 = events["alice"][3]
    # lina's earliest event after alice's day-3 anchor (lina day0 = 04-21)
    l0 = events["lina"][0]
    questions.append(_q(
        "cross_person", "lina", a3, l0,
        f"After {a3['person']} {a3['action']} on {a3['date']}, "
        f"what did lina do next?",
        anchor_expected=a3["content"],
    ))
    return engine, questions


def _q(kind: str, person: str, anchor: dict, target: dict, question: str,
        anchor_expected: str | None = None) -> dict:
    return {
        "kind": kind,
        "person": person,
        "q": question,
        "expected": [target["content"]],
        "anchor_expected": anchor_expected or anchor["content"],
    }


def evaluate(engine: MemoryEngine, questions: list[dict],
             temporal_reason: bool) -> dict:
    stats: dict[str, dict] = {}
    details = []
    for q in questions:
        stats.setdefault(q["kind"], {"n": 0, "hit1": 0, "hit5": 0})["n"] += 1
        results = engine.recall(
            q["q"], top_k=5, temporal_reason=temporal_reason
        )
        contents = [r.item.content for r in results]
        hit1 = bool(contents) and contents[0] == q["expected"][0]
        hit5 = q["expected"][0] in contents
        anchor_hit5 = q["anchor_expected"] in contents
        rank = (contents.index(q["expected"][0]) + 1) if hit5 else 0
        stats[q["kind"]]["hit1"] += int(hit1)
        stats[q["kind"]]["hit5"] += int(hit5)
        stats[q["kind"]]["rank_sum"] = (
            stats[q["kind"]].get("rank_sum", 0) + rank
        )
        stats[q["kind"]]["ranked"] = (
            stats[q["kind"]].get("ranked", 0) + int(rank > 0)
        )
        details.append(
            {
                "kind": q["kind"],
                "q": q["q"],
                "hit1": hit1,
                "hit5": hit5,
                "anchor_hit5": anchor_hit5,
                "rank": rank,
                "top": contents,
            }
        )
    total = {
        "n": sum(v["n"] for v in stats.values()),
        "hit1": sum(v["hit1"] for v in stats.values()),
        "hit5": sum(v["hit5"] for v in stats.values()),
    }
    return {"total": total, "kinds": stats, "details": details}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "reasoning_mini_bench.json"),
    )
    args = parser.parse_args()
    engine, questions = build()
    on = evaluate(engine, questions, temporal_reason=True)
    off = evaluate(engine, questions, temporal_reason=False)
    report = {
        "n": len(questions),
        "on": on["total"],
        "off": off["total"],
        "kinds_on": on["kinds"],
        "kinds_off": off["kinds"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
