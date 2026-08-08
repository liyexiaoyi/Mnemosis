"""Dedupe-memories eval (round 114, McClelland et al. 1995).

10 stores, each with 2-5 copies of one repeated episode plus unique
items. dedupe_memories() should merge exactly the duplicate count and
reduce the active count accordingly.
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
    copies = 2 + seed % 4
    for _ in range(copies):
        engine.remember(
            f"重复{seed}：同一天去了公园。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"公园{seed}", "同一天"],
        )
    for i in range(5):
        engine.remember(
            f"唯一{seed}-{i}：去了{seed}-{i}。",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"唯一{seed}-{i}"],
        )
    return engine


def _run() -> dict:
    count_ok = 0
    reduce_ok = 0
    for seed in range(10):
        engine = _store(seed)
        copies = 2 + seed % 4
        before = len(engine.store.all_active())
        merged = engine.dedupe_memories()
        after = len(engine.store.all_active())
        count_ok += int(merged == copies - 1)
        reduce_ok += int(after == before - (copies - 1))
    return {
        "stores": 10,
        "count_matches": count_ok,
        "reduce_matches": reduce_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "dedupe_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = (
        report["count_matches"] == 10 and report["reduce_matches"] == 10
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
