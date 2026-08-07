"""Pattern-separation benchmark (Bakker et al., 2008, Science).

Similar-but-distinct memories (same date/place, different person, or same
person/place, different date) must not crowd each other out. Each trial stores
two near-duplicate episodes plus distractors; a query with a unique cue should
pick the right one as top-1. We compare top-1 discrimination and the winner's
margin with separation on vs off.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


PLACES = ["aquarium", "art museum", "planetarium", "harbor", "opera house"]
OBJECTS = ["notebook", "camera", "coffee beans", "sketchbook", "vinyl record"]


def build_trial(seed: int, kind: str) -> tuple[MemoryEngine, str, str]:
    rng = random.Random(seed)
    person_a = f"user{seed}"
    person_b = f"user{seed + 1000}"
    day = f"2026-{1 + seed % 12:02d}-{1 + seed % 27:02d}"
    day2 = f"2026-{1 + (seed * 5) % 12:02d}-{1 + (seed * 2) % 27:02d}"
    place = rng.choice(PLACES)
    obj = rng.choice(OBJECTS)
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    if kind == "person":
        a = f"{person_a} visited the {place} on {day}."
        b = f"{person_b} visited the {place} on {day}."
        c = f"{person_a} visited the {rng.choice(PLACES)} on {day2}."
        d = f"{person_b} visited the {rng.choice(PLACES)} on {day2}."
        query = f"{person_a} {place} {day}"
    else:  # date
        a = f"{person_a} visited the {place} on {day}."
        b = f"{person_a} visited the {place} on {day2}."
        c = f"{person_a} bought a {obj} on {day}."
        d = f"{person_a} bought a {obj} on {day2}."
        query = f"{person_a} {place} {day}"
    for content in (a, b, c, d):
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[person_a.lower(), content.split(" on ")[1].rstrip(".")],
            importance=0.5,
            auto_cues=False,
        )
    return engine, query, a


def run(trials: int, separation: bool, kind: str) -> dict:
    top1 = 0
    margins = []
    for seed in range(trials):
        engine, query, target = build_trial(seed, kind)
        results = engine.recall(
            query, top_k=4, separation=separation
        )
        if results and results[0].item.content == target:
            top1 += 1
        # margin between winner and runner-up
        if len(results) >= 2:
            margins.append(results[0].score - results[1].score)
        engine.close()
    return {
        "kind": kind,
        "separation": separation,
        "trials": trials,
        "top1": top1,
        "avg_margin": round(sum(margins) / len(margins), 3) if margins else 0.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "pattern_separation_eval.json"
        ),
    )
    args = parser.parse_args()
    report = {
        "person": {
            "on": run(args.trials, True, "person"),
            "off": run(args.trials, False, "person"),
        },
        "date": {
            "on": run(args.trials, True, "date"),
            "off": run(args.trials, False, "date"),
        },
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
