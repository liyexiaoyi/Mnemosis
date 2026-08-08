"""Cleanup-preview eval (round 121).

10 stores, each with 3 prunable episodic traces (low importance, never
accessed, old) plus protected ones (important / accessed / semantic).
cleanup_preview() should list exactly the 3 candidates without deleting
anything.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(3):
        engine.remember(
            f"c{seed}-{i} prunable",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=[f"c{seed}-{i}"],
            importance=0.1,
            created_at=now - timedelta(days=40),
        )
    engine.remember(
        f"c{seed} important",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=[f"c{seed}-imp"],
        importance=0.8,
        created_at=now - timedelta(days=40),
    )
    accessed = engine.remember(
        f"c{seed} accessed",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=[f"c{seed}-acc"],
        importance=0.1,
        created_at=now - timedelta(days=40),
    )
    accessed.access_count = 2
    engine.backend.update(accessed)
    engine.remember(
        f"c{seed} semantic",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"c{seed}-sem"],
        importance=0.1,
        created_at=now - timedelta(days=40),
    )
    return engine


def _run() -> dict:
    count_ok = 0
    intact_ok = 0
    fields_ok = 0
    for seed in range(10):
        engine = _store(seed)
        now = utcnow()
        before = len(engine.store.all_active())
        preview = engine.cleanup_preview(now=now)
        count_ok += int(len(preview) == 3)
        intact_ok += int(len(engine.store.all_active()) == before)
        fields_ok += int(
            all(
                {"id", "preview", "importance", "age_days"}
                <= set(entry)
                for entry in preview
            )
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "intact_ok": intact_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "cleanup_preview_eval.json"),
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
