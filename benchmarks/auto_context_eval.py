"""Auto-context tagging eval (round 71).

12 memories across 3 locations (会议室/餐厅/图书馆, 4 each), all sharing
the ambiguous cue "方案" and no location word in the query. When
remember() auto-extracts the location into item.context, fuzzy context
recall ("正在会议室里开会") can disambiguate; without tagging it cannot.
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

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

LOCATIONS = ["会议室", "餐厅", "图书馆"]


def _build_engine(auto_context: bool) -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    i = 0
    for loc in LOCATIONS:
        for _ in range(4):
            engine.remember(
                f"阿丽在{loc}里讨论了方案{i}。",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=["方案"],
                importance=0.5,
                strength=0.5,
                auto_cues=False,
                auto_context=auto_context,
            )
            i += 1
    return engine


def _run(auto_context: bool) -> dict:
    engine = _build_engine(auto_context)
    tagged = sum(
        1 for item in engine.store.all_active() if item.context is not None
    )
    hits = 0
    for loc in LOCATIONS:
        results = engine.recall(
            "刚才讨论的方案是什么？",
            top_k=4,
            context=f"正在{loc}里开会",
        )
        if loc in results[0].item.content:
            hits += 1
    return {
        "auto_context": auto_context,
        "tagged": tagged,
        "location_hits": hits,
        "hit_ratio": round(hits / len(LOCATIONS), 3),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "auto_context_eval.json"),
    )
    args = parser.parse_args()
    report = {
        "auto": _run(True),
        "no_auto": _run(False),
    }
    report["all_ok"] = bool(
        report["auto"]["tagged"] == 12
        and report["auto"]["location_hits"] == len(LOCATIONS)
        and report["auto"]["location_hits"]
        > report["no_auto"]["location_hits"]
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
