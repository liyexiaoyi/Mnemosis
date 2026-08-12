"""Schema-report eval (round 131, Bartlett 1932).

10 stores. Each store: 3 memories cued "工作", 2 cued "生活" (one
semantic + one episodic) and 1 uncued memory. schema_report must cluster
them into 3 topic groups with correct counts, kinds, ordering and fields.
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
    for i in range(3):
        engine.remember(
            f"work item {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["工作"],
            importance=0.8,
            auto_cues=False,
        )
    engine.remember(
        f"life fact {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["生活"],
        auto_cues=False,
    )
    engine.remember(
        f"life event {seed}",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["生活"],
        auto_cues=False,
    )
    engine.remember(
        f"zzz none {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        auto_cues=False,
    )
    return engine


def _run() -> dict:
    group_ok = count_ok = top_ok = kinds_ok = total_ok = fields_ok = 0
    for seed in range(10):
        engine = _store(seed)
        report = engine.schema_report(limit=10)
        top = report["top_groups"]
        group_ok += int(report["group_count"] == 3)
        by_topic = {g["topic"]: g for g in top}
        count_ok += int(
            by_topic["工作"]["memory_count"] == 3
            and by_topic["生活"]["memory_count"] == 2
            and by_topic["（无标签）"]["memory_count"] == 1
        )
        top_ok += int(top[0]["topic"] == "工作")
        kinds_ok += int(
            by_topic["生活"]["kinds"]
            == {"semantic": 1, "episodic": 1}
        )
        total_ok += int(report["total_memories"] == 6)
        fields_ok += int(
            {"total_memories", "group_count", "top_groups"} <= set(report)
            and all(
                {"topic", "memory_count", "avg_importance", "kinds",
                 "samples"} <= set(g)
                and g["samples"]
                for g in top
            )
        )
    return {
        "stores": 10,
        "group_ok": group_ok,
        "count_ok": count_ok,
        "top_ok": top_ok,
        "kinds_ok": kinds_ok,
        "total_ok": total_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "schema_report_eval.json"),
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
