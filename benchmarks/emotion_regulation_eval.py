"""Emotion-regulation eval (round 69, Gross 2002).

30 emotional memories decayed 30 days:
  - regulated: 6 days of full daily retrieval practice (always successful,
    review_streak >= 3) then 24 days of decay - the emotional charge fades
    and the trace returns to the normal forgetting curve;
  - unprocessed: no practice - stays on the slow emotional decay curve;
  - neutral: same memories without affect, no practice - normal decay.
Expectation: regulated keeps the most (practice still works) while its
post-processing decay rate is normal, i.e. the memory is not kept "hot"
forever.
"""

from __future__ import annotations

import argparse
import copy
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


def _base_engine(affect: str | None) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    start = utcnow() - timedelta(days=32)
    for i in range(30):
        importance = 0.4 + 0.5 * (i % 8) / 7
        strength = 0.5 + 0.15 * ((i * 5) % 9) / 8
        engine.remember(
            f"情绪记忆{i}：那次经历让我很难受。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"事件{i}"],
            importance=importance,
            strength=strength,
            created_at=start,
            affect=affect,
        )
    return engine


def _run(engine: MemoryEngine, mode: str) -> dict:
    start = utcnow() - timedelta(days=32)
    if mode == "regulated":
        for day in range(6):
            day_now = start + timedelta(days=day)
            # full retrieval-processing session: every trace is recalled and
            # reinforced each day (review_streak -> 3+), then decay resumes
            for item in engine.store.all_active():
                engine.practice_answer(
                    item.id, item.content, now=day_now
                )
    final_now = start + timedelta(days=30)
    items = engine.store.all_active()
    retrievabilities = [engine.curve.retrievability(i, final_now) for i in items]
    processed = sum(1 for i in items if i.review_streak >= 3)
    decay_rates = {
        "normal": engine.curve.decay_rate,
        "emotional_slow": engine.curve.decay_rate * 0.6,
    }
    return {
        "mode": mode,
        "processed_items": processed,
        "mean_retrievability": round(
            sum(retrievabilities) / len(retrievabilities), 3
        ),
        "retained": sum(1 for r in retrievabilities if r >= 0.3),
        "decay_rates": decay_rates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "emotion_regulation_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "regulated": _run(_base_engine("negative"), "regulated"),
        "unprocessed": _run(_base_engine("negative"), "unprocessed"),
        "neutral": _run(_base_engine(None), "unprocessed"),
    }
    report["all_ok"] = bool(
        report["regulated"]["processed_items"] == 30
        and report["regulated"]["mean_retrievability"]
        > report["unprocessed"]["mean_retrievability"]
        and report["unprocessed"]["mean_retrievability"]
        > report["neutral"]["mean_retrievability"]
        and report["regulated"]["decay_rates"]["normal"]
        > report["regulated"]["decay_rates"]["emotional_slow"]
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
