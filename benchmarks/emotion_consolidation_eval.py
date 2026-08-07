"""Amygdala-modulated emotional consolidation benchmark.

McGaugh (2004): emotional arousal strengthens consolidation. Krenz et al.
(2025, J. Neurosci.): recurring emotional events get a memory boost. We
measure, over 20 recurring "events" (10 emotional, 10 neutral, each repeated
3 times), how sleep consolidation + 30 days of decay affect retention:

- retrievability after 30 days (emotional vs neutral);
- confidence of the surviving trace (emotional vs neutral);
- link strength inside emotional clusters vs neutral pairs;
- recall hit rate with a partial cue.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import datetime, timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


EMOTIONS = ["negative", "positive", "arousing"]
VERBS = ["missed", "won", "rescued", "celebrated", "argued", "discovered"]
NOUNS = ["deadline", "contract", "launch", "interview", "exam", "audit"]
NEUTRAL_VERBS = ["read", "reviewed", "filed", "scheduled", "logged", "checked"]
NEUTRAL_NOUNS = ["report", "calendar", "spreadsheet", "inbox", "agenda", "notes"]


def _day(seed: int, i: int) -> str:
    return f"2026-{1 + (seed + i) % 12:02d}-{1 + (seed * 3 + i) % 27:02d}"


def build(seed: int) -> MemoryEngine:
    rng = random.Random(seed)
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(10):
        person = f"user{i}"
        emo_verb_a, emo_verb_b = rng.sample(VERBS, 2)
        neu_verb_a, neu_verb_b = rng.sample(NEUTRAL_VERBS, 2)
        # unique nouns per user avoid cross-user cue collisions
        emo_noun = f"topic{i}"
        neu_noun = f"item{i}"
        day_a, day_b = _day(seed, i * 2), _day(seed, i * 2 + 1)
        emotion_a = f"{person} {emo_verb_a} the {emo_noun} on {day_a}."
        emotion_b = f"{person} {emo_verb_b} the {emo_noun} on {day_b}."
        neutral_a = f"{person} {neu_verb_a} the {neu_noun} on {day_a}."
        neutral_b = f"{person} {neu_verb_b} the {neu_noun} on {day_b}."
        for _ in range(2):
            engine.remember(
                emotion_a,
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=[person.lower(), emo_noun],
                importance=0.65,
                confidence=0.85,
                strength=0.85,
                affect="negative",
                created_at=now - timedelta(days=60),
            )
            engine.remember(
                emotion_b,
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=[person.lower(), emo_noun],
                importance=0.65,
                confidence=0.85,
                strength=0.85,
                affect="negative",
                created_at=now - timedelta(days=60),
            )
            engine.remember(
                neutral_a,
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=[person.lower(), neu_noun],
                importance=0.65,
                confidence=0.85,
                strength=0.85,
                created_at=now - timedelta(days=60),
            )
            engine.remember(
                neutral_b,
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=[person.lower(), neu_noun],
                importance=0.65,
                confidence=0.85,
                strength=0.85,
                created_at=now - timedelta(days=60),
            )
    engine.sleep(now=now)
    return engine


def run(seed: int = 7) -> dict:
    engine = build(seed)
    now = utcnow()
    after = now + timedelta(days=30)

    def tag(item) -> str:
        return item.affect if item.affect else "neutral"

    active = engine.backend.list()
    by_tag: dict[str, list] = {"negative": [], "neutral": []}
    for item in active:
        by_tag.setdefault(tag(item), []).append(item)

    def avg(items, attr):
        return round(sum(getattr(i, attr) for i in items) / len(items), 3)

    emotional = by_tag["negative"]
    neutral = by_tag["neutral"]
    emo_ret = engine.curve.retrievability
    ret_emo = round(
        sum(emo_ret(i, after) for i in emotional) / len(emotional), 3
    )
    ret_neu = round(
        sum(emo_ret(i, after) for i in neutral) / len(neutral), 3
    )
    conf_emo = avg(emotional, "confidence")
    conf_neu = avg(neutral, "confidence")
    storage_emo = avg(emotional, "storage_strength")
    storage_neu = avg(neutral, "storage_strength")

    # partial-cue recall: ask for the emotional/neutral event by person+noun
    emo_hits = neu_hits = 0
    for i in range(10):
        person = f"user{i}"
        emo_items = [it for it in emotional if it.cues[0] == person.lower()]
        neu_items = [it for it in neutral if it.cues[0] == person.lower()]
        emo_noun = emo_items[0].cues[1]
        neu_noun = neu_items[0].cues[1]
        emo_res = engine.recall(
            f"{person} {emo_noun}", top_k=3, now=after
        )
        neu_res = engine.recall(
            f"{person} {neu_noun}", top_k=3, now=after
        )
        emo_contents = {r.item.content for r in emo_res}
        neu_contents = {r.item.content for r in neu_res}
        emo_hits += int(
            any(it.content in emo_contents for it in emo_items)
        )
        neu_hits += int(
            any(it.content in neu_contents for it in neu_items)
        )

    # emotional cluster link strength vs neutral
    emo_links = []
    neu_links = []
    for i in range(10):
        person = f"user{i}"
        emo_items = [it for it in emotional if it.cues[0] == person.lower()]
        neu_items = [it for it in neutral if it.cues[0] == person.lower()]
        if len(emo_items) >= 2:
            emo_links.append(
                engine.backend.link_weight(emo_items[0].id, emo_items[1].id)
            )
        if len(neu_items) >= 2:
            neu_links.append(
                engine.backend.link_weight(neu_items[0].id, neu_items[1].id)
            )
    engine.close()
    return {
        "events_per_condition": 20,
        "repeats_per_event": 2,
        "retention_30d": {"emotional": ret_emo, "neutral": ret_neu,
                          "delta": round(ret_emo - ret_neu, 3)},
        "confidence": {"emotional": conf_emo, "neutral": conf_neu,
                       "delta": round(conf_emo - conf_neu, 3)},
        "storage_strength": {"emotional": storage_emo, "neutral": storage_neu},
        "partial_cue_recall_top3": {"emotional": emo_hits, "neutral": neu_hits},
        "avg_internal_link_weight": {
            "emotional": round(sum(emo_links) / len(emo_links), 2)
            if emo_links else 0.0,
            "neutral": round(sum(neu_links) / len(neu_links), 2)
            if neu_links else 0.0,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument(
        "--out",
        default=os.path.join(
            os.path.dirname(__file__), "results", "emotion_consolidation.json"
        ),
    )
    args = parser.parse_args()
    reports = [run(args.seed + i) for i in range(args.runs)]
    report = {"runs": reports}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
