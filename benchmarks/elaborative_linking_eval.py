"""Elaborative co-retrieval linking eval (round 62).

20 memories in 10 unrelated pairs (A_i, B_i), no shared cues
(auto_cues=False). Phase 1: one retrieval per pair with both cues in the
query, so A_i and B_i co-occur (linking ON or OFF). Phase 2: retrieve with
only A_i's cue; a linked B_i should surface via spreading activation even
though it shares no words with the query (Craik & Tulving, 1975;
Collins & Loftus, 1975).
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


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for i in range(10):
        for side in ("a", "b"):
            cue = f"topic{i}_{side}"
            engine.remember(
                f"note number {i} side {side}",
                kind=MemoryKind.SEMANTIC,
                source=source,
                cues=[cue],
                importance=0.5,
                strength=0.5,
                auto_cues=False,
            )
    return engine


def _run(elaborate: bool) -> dict:
    engine = _build_engine()
    hits = 0
    ranks = []
    for i in range(10):
        a_cue = f"topic{i}_a"
        b_cue = f"topic{i}_b"
        # phase 1: both cues co-occur in one retrieval act
        engine.recall(
            f"{a_cue} {b_cue}",
            top_k=5,
            elaborate_links=elaborate,
        )
        # phase 2: only A's cue; B must come via the association
        results = engine.recall(
            a_cue,
            top_k=3,
            elaborate_links=False,
        )
        for rank, res in enumerate(results, start=1):
            if res.item.cues and res.item.cues[0] == b_cue:
                hits += 1
                ranks.append(rank)
                break
    return {
        "elaborate": elaborate,
        "linked_hits": hits,
        "hit_ratio": round(hits / 10, 3),
        "avg_rank": round(sum(ranks) / len(ranks), 3) if ranks else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "elaborative_linking_eval.json"
        ),
    )
    args = parser.parse_args()
    report = {
        "linked": _run(True),
        "unlinked": _run(False),
    }
    report["all_ok"] = bool(
        report["linked"]["linked_hits"] > report["unlinked"]["linked_hits"]
        and report["unlinked"]["linked_hits"] == 0
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
