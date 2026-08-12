"""Second-look recall eval (round 84, Koriat & Goldsmith 1996).

8 cue conflicts: a weaker-evidence memory (evidence 1, slightly stronger
strength) wins the single pass by a tiny margin (shaky top-1). The
second look re-ranks by evidence strength and source trust, so the
evidence-backed memory (evidence 3) should win 8/8.
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

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow

VARIANTS = [
    (0.70, 0.55, 0.60, 0.50),
    (0.72, 0.57, 0.61, 0.51),
    (0.68, 0.53, 0.59, 0.49),
    (0.74, 0.59, 0.62, 0.52),
    (0.69, 0.54, 0.58, 0.48),
    (0.71, 0.56, 0.63, 0.53),
    (0.73, 0.58, 0.60, 0.50),
    (0.67, 0.52, 0.61, 0.51),
]


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow() - timedelta(days=10)
    for i, (imp_w, imp_s, str_w, str_s) in enumerate(VARIANTS):
        engine.remember(
            f"alpha{i} weak",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"alpha{i}"],
            importance=imp_w,
            strength=str_w,
            evidence_count=1,
            created_at=now,
            auto_cues=False,
        )
        engine.remember(
            f"alpha{i} strong",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"alpha{i}"],
            importance=imp_s,
            strength=str_s,
            evidence_count=3,
            created_at=now,
            auto_cues=False,
        )
    return engine


def _run(second_look: bool) -> dict:
    engine = _build_engine()
    hits = 0
    shaky = 0
    for i in range(8):
        results = engine.recall(
            f"alpha{i}",
            top_k=3,
            second_look=second_look,
            corroboration_boost=False,
        )
        if not results[0].confident:
            shaky += 1
        if results[0].item.content.endswith("strong"):
            hits += 1
    return {
        "second_look": second_look,
        "evidence_first": hits,
        "hit_ratio": round(hits / 8, 3),
        "shaky_top": shaky,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "second_look_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "second_look": _run(True),
        "single_pass": _run(False),
    }
    report["all_ok"] = bool(
        report["second_look"]["evidence_first"] == 8
        and report["single_pass"]["evidence_first"] == 0
        and report["single_pass"]["shaky_top"] == 8
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
