"""Context-dependent memory eval (round 60, Godden & Baddeley 1975).

15 memories across 3 stored contexts (办公室/会议室/家里, 5 each), all
sharing the ambiguous cue "采购". Queries are just "采购" (all 15 match);
the only disambiguator is the current context. Modes:
  - fuzzy (new): partial context overlap "在会议室里开会" vs stored
    "会议室" boosts the matching context;
  - exact: context string equals the stored context;
  - no_boost: context passed but context_boost=False;
  - no_context: no context at all.
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

CONTEXTS = ["办公室", "会议室", "家里"]
PER_CTX = 5


def _base_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    start = utcnow() - timedelta(days=7)
    idx = 0
    for ctx in CONTEXTS:
        for i in range(PER_CTX):
            engine.remember(
                f"{ctx}记录{idx}：编号{idx}的事项已经完成。",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=["采购", f"事项{idx}"],
                context=ctx,
                importance=0.5,
                strength=0.5,
                created_at=start,
                auto_cues=False,
            )
            idx += 1
    return engine


def _run(engine: MemoryEngine, mode: str) -> dict:
    first = 0
    best_ranks = []
    for ctx in CONTEXTS:
        if mode == "fuzzy":
            context, context_boost = f"正在{ctx}里开会", True
        elif mode == "exact":
            context, context_boost = ctx, True
        elif mode == "no_boost":
            context, context_boost = f"正在{ctx}里开会", False
        else:  # no_context
            context, context_boost = None, True
        results = engine.recall(
            "采购",
            top_k=10,
            context=context,
            context_boost=context_boost,
        )
        rank = None
        for i, res in enumerate(results, start=1):
            if res.item.context == ctx:
                rank = i
                break
        if rank == 1:
            first += 1
        best_ranks.append(rank or len(results) + 1)
    return {
        "mode": mode,
        "top1_correct": first,
        "top1_ratio": round(first / len(CONTEXTS), 3),
        "avg_best_rank": round(
            sum(best_ranks) / len(best_ranks), 3
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "context_dependent_eval.json"
        ),
    )
    args = parser.parse_args()
    report = {}
    for mode in ("fuzzy", "exact", "no_boost", "no_context"):
        report[mode] = _run(_base_engine(), mode)
        print(report[mode], flush=True)
    report["all_ok"] = bool(
        report["fuzzy"]["top1_correct"]
        >= report["no_boost"]["top1_correct"]
        and report["fuzzy"]["top1_correct"]
        >= report["no_context"]["top1_correct"]
        and report["exact"]["top1_correct"] >= report["fuzzy"]["top1_correct"]
        and report["fuzzy"]["avg_best_rank"]
        < report["no_boost"]["avg_best_rank"]
        and report["fuzzy"]["avg_best_rank"]
        < report["no_context"]["avg_best_rank"]
    )
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
