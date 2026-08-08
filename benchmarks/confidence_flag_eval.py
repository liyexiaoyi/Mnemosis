"""Recall confidence-flag eval (round 72, Koriat & Goldsmith 1996).

12 cue conflicts: 6 with a clear winner (importance 0.9 vs 0.5) and 6
fully ambiguous (equal memories). The top RecallResult should carry
confident=True only when the answer is actually clear, so agents know
when to hedge ("我不太确定").
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


def _engine(kind: str) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for i in range(6):
        cue = f"cue{i}"
        if kind == "clear":
            engine.remember(
                f"{cue} winner",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[cue],
                importance=0.9,
                strength=0.5,
                auto_cues=False,
            )
            engine.remember(
                f"{cue} rival",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[cue],
                importance=0.5,
                strength=0.5,
                auto_cues=False,
            )
        else:
            for content in (f"{cue} one", f"{cue} two"):
                engine.remember(
                    content,
                    kind=MemoryKind.SEMANTIC,
                    source=source,
                    cues=[cue],
                    importance=0.5,
                    strength=0.5,
                    auto_cues=False,
                )
    return engine


def _run(kind: str) -> dict:
    engine = _engine(kind)
    flagged = 0
    gaps = []
    for i in range(6):
        results = engine.recall(f"cue{i}", top_k=3)
        if results[0].confident:
            flagged += 1
        second = results[1].score if len(results) > 1 else -1.0
        gaps.append(round(results[0].score - second, 4))
    return {
        "kind": kind,
        "confident_flags": flagged,
        "expected": 6 if kind == "clear" else 0,
        "avg_gap": round(sum(gaps) / len(gaps), 4),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "confidence_flag_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "clear": _run("clear"),
        "ambiguous": _run("ambiguous"),
    }
    report["all_ok"] = bool(
        report["clear"]["confident_flags"] == 6
        and report["ambiguous"]["confident_flags"] == 0
        and report["clear"]["avg_gap"] > report["ambiguous"]["avg_gap"]
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
