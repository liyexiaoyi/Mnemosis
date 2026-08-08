"""Encoding-variability eval (round 74, Martin 1968).

30 memories, each stored under three cues, decayed 32 days; 14 days of
daily practice (quota 4, 24h gap):
  - varied: practice_due(vary_cues=True) rotates which cue is shown;
  - fixed: always shows the same first-two cue pair (cue C is never shown);
  - none.
Final test asks each memory through cue C (the cue fixed practice never
shows): retrieval is more likely when cue C was actually rehearsed
(factor 1.0 if shown, else 0.75).
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import random
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _base_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    start = utcnow() - timedelta(days=32)
    for i in range(30):
        importance = 0.4 + 0.5 * (i % 8) / 7
        strength = 0.5 + 0.15 * ((i * 5) % 9) / 8
        engine.remember(
            f"变异性记忆{i}：内容编号{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"线索A{i}", f"线索B{i}", f"线索C{i}"],
            importance=importance,
            strength=strength,
            created_at=start,
            auto_cues=False,
        )
    return engine


def _simulate(engine: MemoryEngine, mode: str, seed: int) -> dict:
    rng = random.Random(seed)
    now = utcnow() - timedelta(days=32)
    shown: dict[str, int] = {}
    if mode != "none":
        for day in range(14):
            day_now = now + timedelta(days=day)
            due = engine.practice_due(
                limit=4,
                now=day_now,
                min_gap_hours=24.0,
                adaptive_gap=False,
                vary_cues=mode == "varied",
            )
            for card in due:
                item = engine.backend.get(card["id"])
                if item is None:
                    continue
                if "线索c" in card["cue"].lower():
                    shown[item.id] = shown.get(item.id, 0) + 1
                retrievability = engine.curve.retrievability(item, day_now)
                ok = rng.random() < retrievability
                engine.practice_answer(
                    item.id,
                    item.content if ok else "错误答案",
                    now=day_now,
                )
    final_now = now + timedelta(days=14)
    successes = 0
    cue_c_shown = 0
    for item in engine.store.all_active():
        c_count = shown.get(item.id, 0)
        cue_c_shown += int(c_count >= 1)
        retrievability = engine.curve.retrievability(item, final_now)
        factor = 1.0 if c_count >= 1 else 0.75
        if rng.random() < retrievability * factor:
            successes += 1
    return {
        "mode": mode,
        "final_successes": successes,
        "success_ratio": round(successes / 30, 3),
        "cue_c_shown": cue_c_shown,
        "cue_c_ratio": round(cue_c_shown / 30, 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "encoding_variability_eval.json"
        ),
    )
    args = parser.parse_args()
    base = _base_engine()
    report = {
        "varied": _simulate(copy.deepcopy(base), "varied", args.seed),
        "fixed": _simulate(copy.deepcopy(base), "fixed", args.seed),
        "none": _simulate(copy.deepcopy(base), "none", args.seed),
    }
    report["all_ok"] = bool(
        report["varied"]["final_successes"]
        > report["fixed"]["final_successes"]
        and report["fixed"]["final_successes"]
        > report["none"]["final_successes"]
        and report["varied"]["cue_c_shown"]
        > report["fixed"]["cue_c_shown"]
    )
    for v in report.values():
        print(v, flush=True)
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
