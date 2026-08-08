"""Search-batch eval (round 126, Miller 1956 working-memory chunking).

10 stores. Each store: 2 target memories (unique cues) + 2 distractors.
A batch of 4 queries (2 hits, 2 misses) must return 4 groups in input
order; hit groups must rank the right target first; miss groups must
score lower than the corresponding hit groups.
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
    a = engine.remember(
        f"alpha target {seed}.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"alpha{seed}-key"],
    )
    b = engine.remember(
        f"beta target {seed}.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"beta{seed}-key"],
    )
    engine.remember(f"qqq dst {seed}-1.", kind=MemoryKind.SEMANTIC, source=user)
    engine.remember(f"rrr dst {seed}-2.", kind=MemoryKind.SEMANTIC, source=user)
    return engine, a.id, b.id


def _run() -> dict:
    count_ok = order_ok = hit_ok = rank_ok = fields_ok = 0
    for seed in range(10):
        engine, aid, bid = _store(seed)
        queries = [
            f"alpha{seed}-key",
            f"beta{seed}-key",
            f"zzz miss {seed}-1",
            f"zzz miss {seed}-2",
        ]
        groups = engine.search_batch(queries, top_k=2)
        count_ok += int(len(groups) == 4)
        order_ok += int([g["query"] for g in groups] == queries)
        hit_ok += int(
            groups[0]["results"][0]["id"] == aid
            and groups[1]["results"][0]["id"] == bid
        )
        rank_ok += int(
            groups[2]["results"][0]["score"] < groups[0]["results"][0]["score"]
            and groups[3]["results"][0]["score"] < groups[1]["results"][0]["score"]
        )
        fields_ok += int(
            all(
                {"query", "count", "results"} <= set(g)
                and g["results"]
                and all(
                    {"id", "preview", "score", "confident"} <= set(r)
                    for r in g["results"]
                )
                for g in groups
            )
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "order_ok": order_ok,
        "hit_ok": hit_ok,
        "rank_ok": rank_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "search_batch_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(
        v == 10 for k, v in report.items() if k != "stores"
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
