"""Aged-memory pattern-completion benchmark.

Hypothesis (Rolls, 2013; Theves et al., 2024): a partial cue re-activates a
whole well-integrated pattern, so a weakly retrievable (old, seldom accessed)
memory that is strongly linked to a fresh anchor can be rescued by pattern
completion, even when fresh distractors would otherwise outrank it.

Each trial builds a 4-memory store:
  A  fresh anchor sharing two cues with B (the integrated pattern)
  B  OLD + weak target (the memory we want completed back)
  C  fresh distractor sharing one cue with A (different pattern)
  D  fresh distractor sharing one cue with A (different pattern)

The query is a partial cue that strongly matches B's content but only
partially matches A. Unrelated fillers are placed between A and the others so
spreading activation (which decays with temporal distance) can NOT rescue B,
while pattern completion (which uses cue-sharing + link weight, not temporal
distance) can. We measure whether B is rescued into the top-2/3 with pattern
completion on vs off (A/B control, same stores).
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow

PLACES = [
    "aquarium", "art museum", "planetarium", "old town", "harbor",
    "national park", "opera house", "botanical garden",
]
ITEMS = [
    "notebook", "camera", "coffee beans", "hiking boots", "vinyl record",
    "sketchbook",
]


def build_trial(seed: int) -> tuple[MemoryEngine, str, str]:
    """Return (engine, query, target_content) for one rescue trial."""
    rng = random.Random(seed)
    person = f"person{seed}"
    other = f"person{seed + 1000}"
    day = f"2026-{1 + seed % 12:02d}-{1 + seed % 27:02d}"
    other_day = f"2026-{1 + (seed * 7) % 12:02d}-{1 + (seed * 3) % 27:02d}"
    session = f"session{seed}"
    place = rng.choice(PLACES)
    item = rng.choice(ITEMS)

    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    anchor = f"{person} visited the {place} on {day}."
    target = f"{person} bought a {item} during {session}."
    distractor_c = f"{other} visited the museum on {day}."
    distractor_d = f"{person} met Dana on {other_day}."
    engine.remember(
        anchor,
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=[person.lower(), day, session],
        importance=0.5,
        created_at=now,
    )
    # Unrelated fillers push B/C/D far away in temporal distance from A, so
    # spreading activation's distance-decay cannot rescue B on its own.
    for filler in range(25):
        engine.remember(
            f"Filler{filler + seed * 100} likes topic{filler}.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"filler{filler + seed * 100}"],
            importance=0.5,
            created_at=now,
        )
    engine.remember(
        target,
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=[person.lower(), session],
        importance=0.2,
        created_at=now - timedelta(days=60),
    )
    engine.remember(
        distractor_c,
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=[other.lower(), day],
        importance=0.8,
        created_at=now,
    )
    engine.remember(
        distractor_d,
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=[person.lower(), other_day, f"session{seed + 500}"],
        importance=0.6,
        created_at=now,
    )
    query = f"{person} {item} {session}"
    return engine, query, target


def run_trials(trials: int, pattern_completion: bool) -> dict:
    rescued = 0
    top1 = 0
    ranks: list[int] = []
    for seed in range(trials):
        engine, query, target = build_trial(seed)
        results = engine.recall(
            query,
            top_k=3,
            pattern_completion=pattern_completion,
        )
        contents = [r.item.content for r in results]
        if target in contents:
            rescued += 1
            ranks.append(contents.index(target) + 1)
            if contents.index(target) == 0:
                top1 += 1
        else:
            ranks.append(0)
        engine.close()
    return {
        "trials": trials,
        "pattern_completion": pattern_completion,
        "rescued_top3": rescued,
        "rescued_top1": top1,
        "rank_histogram": {
            str(k): ranks.count(k) for k in sorted(set(ranks))
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=30)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__),
            "results",
            "pattern_completion_eval.json",
        ),
    )
    args = parser.parse_args()
    on = run_trials(args.trials, pattern_completion=True)
    off = run_trials(args.trials, pattern_completion=False)
    report = {
        "on": on,
        "off": off,
        "delta_rescued_top3": on["rescued_top3"] - off["rescued_top3"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
