"""Tag-memories eval (round 119).

10 stores x 10 items; bulk-add 3 tags, then remove 1. Every item must
carry the new tags (and drop the removed one), counts must match, and
recall via a new tag must surface the items.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(10):
        engine.remember(
            f"tag{seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["base"],
            auto_cues=False,
        )
    return engine


def _run() -> dict:
    add_ok = 0
    remove_ok = 0
    count_ok = 0
    recall_ok = 0
    for seed in range(10):
        engine = _store(seed)
        ids = [item.id for item in engine.store.all_active()]
        added = engine.tag_memories(ids, ["工作", "项目", "紧急"], "add")
        items = engine.store.all_active()
        add_ok += int(
            all(
                {"工作", "项目", "紧急"} <= set(item.cues)
                for item in items
            )
        )
        removed = engine.tag_memories(ids, ["项目"], "remove")
        remove_ok += int(
            all("项目" not in item.cues for item in engine.store.all_active())
        )
        count_ok += int(added["added"] == 30 and removed["removed"] == 10)
        top = engine.recall("工作", top_k=5)
        recall_ok += int(len(top) >= 5)
    return {
        "stores": 10,
        "add_ok": add_ok,
        "remove_ok": remove_ok,
        "count_ok": count_ok,
        "recall_ok": recall_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "tag_memories_eval.json"),
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
