"""Memory-status eval (round 104).

10 varied stores (5-50 memories, semantic/episodic mix, some due, some
conflicting). memory_status() should match manual counts for active /
semantic / episodic / due_now / conflicts on every store.
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


def _store(size: int, seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    rng = __import__("random").Random(seed)
    for i in range(size):
        kind = MemoryKind.EPISODIC if i % 3 == 0 else MemoryKind.SEMANTIC
        strength = 0.2 + 0.6 * rng.random()
        engine.remember(
            f"store{seed} item{i}",
            kind=kind,
            source=user,
            cues=[f"store{seed}-{i}"],
            importance=0.5,
            strength=strength,
            confidence=0.8,
            created_at=now - timedelta(days=10 + i),
            auto_cues=False,
        )
    # one guaranteed conflict pair per store
    engine.remember(
        f"store{seed} conflict a",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"store{seed}-conflict"],
        confidence=0.8,
        auto_cues=False,
    )
    engine.remember(
        f"store{seed} conflict b",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"store{seed}-conflict"],
        confidence=0.8,
        auto_cues=False,
    )
    return engine


def _run() -> dict:
    checks = {"active": 0, "semantic": 0, "episodic": 0,
              "due": 0, "conflicts": 0}
    for seed in range(10):
        engine = _store(5 + seed * 5, seed)
        now = utcnow()
        status = engine.memory_status(now=now)
        items = engine.store.all_active()
        manual = {
            "active": len(items),
            "semantic": sum(
                1 for i in items if i.kind is MemoryKind.SEMANTIC
            ),
            "episodic": sum(
                1 for i in items if i.kind is MemoryKind.EPISODIC
            ),
            "due": len(
                engine.scheduler.due_items(items, now=now, limit=10**6)
            ),
            "conflicts": len(engine.consolidator.detect_conflicts()),
        }
        checks["active"] += int(status["stats"]["active"] == manual["active"])
        checks["semantic"] += int(
            status["stats"]["semantic"] == manual["semantic"]
        )
        checks["episodic"] += int(
            status["stats"]["episodic"] == manual["episodic"]
        )
        checks["due"] += int(status["due_now"] == manual["due"])
        checks["conflicts"] += int(status["conflicts"] == manual["conflicts"])
    return {k: v for k, v in checks.items()}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "memory_status_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(v == 10 for v in report.values())
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
