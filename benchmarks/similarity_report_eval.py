"""Similarity-report eval (round 124, Yassa & Stark 2011).

10 stores, each with 3 confusable pairs (near-identical content, ~0.75
token overlap) and 3 clearly different pairs. similarity_report(threshold=0.6)
should surface exactly the 3 confusable pairs with overlap fields.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    confusable = [
        ("zulu alpha record", "zulu alpha records"),
        ("mike bravo report", "mike bravo reports"),
        ("kilo tango delta", "kilo tango deltas"),
    ]
    for i, (a_text, b_text) in enumerate(confusable):
        engine.remember(
            f"confuse-{seed}-{i}: {a_text}.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"sim{seed}-{i}a"],
        )
        engine.remember(
            f"confuse-{seed}-{i}: {b_text}.",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"sim{seed}-{i}b"],
        )
    for i in range(3):
        engine.remember(
            f"qwerty{seed}-{i} aaa",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"dif{seed}-{i}a"],
        )
        engine.remember(
            f"zxcvbnm{seed}-{i} bbb",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"dif{seed}-{i}b"],
        )
    return engine


def _run() -> dict:
    count_ok = 0
    correct_ok = 0
    fields_ok = 0
    for seed in range(10):
        engine = _store(seed)
        report = engine.similarity_report(threshold=0.6)
        count_ok += int(len(report) == 3)
        correct_ok += int(
            all(
                p["overlap"] >= 0.6
                and "confuse" in p["a_preview"] + p["b_preview"]
                and p["a_preview"] != p["b_preview"]
                for p in report
            )
        )
        fields_ok += int(
            all(
                {"a_id", "b_id", "overlap", "a_preview", "b_preview"}
                <= set(p)
                for p in report
            )
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "correct_ok": correct_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "similarity_report_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(v == 10 for k, v in report.items() if k != "stores")
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
