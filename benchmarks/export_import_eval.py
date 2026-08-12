"""Export/import eval (round 106).

10 stores of 20 memories with varied stats; export -> import into a fresh
engine. Counts must match (20/20), every item must round-trip exactly, and
recall must return the same top-1 on 5 queries per store.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    rng = random.Random(seed)
    for i in range(20):
        kind = MemoryKind.EPISODIC if i % 4 == 0 else MemoryKind.SEMANTIC
        item = engine.remember(
            f"seed{seed} item{i} value{i}",
            kind=kind,
            source=user,
            cues=[f"seed{seed}-{i}"],
            importance=0.4 + 0.5 * rng.random(),
            strength=0.3 + 0.6 * rng.random(),
            confidence=0.7 + 0.2 * rng.random(),
            created_at=now - timedelta(days=1 + i),
            auto_cues=False,
        )
        item.retrieval_successes = rng.randint(0, 4)
        item.retrieval_failures = rng.randint(0, 2)
        item.review_streak = rng.randint(0, 3)
        engine.backend.update(item)
    return engine


def _run() -> dict:
    counts = 0
    exact = 0
    recall = 0
    for seed in range(10):
        src = _store(seed)
        payload = src.export_memories()
        dst = MemoryEngine()
        imported = dst.import_memories(payload)
        counts += int(imported == 20)
        src_items = {
            i.id: {
                k: v for k, v in i.to_dict().items() if k != "seq"
            }
            for i in src.store.all_active()
        }
        dst_items = {
            i.id: {
                k: v for k, v in i.to_dict().items() if k != "seq"
            }
            for i in dst.store.all_active()
        }
        exact += int(src_items == dst_items)
        for q in range(5):
            query = f"seed{seed}-{q}"
            s_top = src.recall(query, top_k=1)
            d_top = dst.recall(query, top_k=1)
            if (
                s_top
                and d_top
                and s_top[0].item.content == d_top[0].item.content
            ):
                recall += 1
    return {
        "stores": 10,
        "count_matches": counts,
        "exact_roundtrips": exact,
        "recall_matches": recall,
        "recall_total": 50,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "export_import_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["count_matches"] == 10
        and report["exact_roundtrips"] == 10
        and report["recall_matches"] == report["recall_total"]
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
