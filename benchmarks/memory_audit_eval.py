"""Memory-audit eval (round 111).

10 varied stores (semantic/episodic, revised, emotional, recycled,
conflicts). memory_audit() must match manual computation on every metric.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, MemoryStatus, SourceRecord, SourceType, utcnow  # noqa: E402


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    rng = random.Random(seed)
    for i in range(20):
        kind = MemoryKind.EPISODIC if i % 4 == 0 else MemoryKind.SEMANTIC
        item = engine.remember(
            f"audit{seed}-{i}",
            kind=kind,
            source=user,
            cues=[f"audit{seed}-{i}"],
            importance=0.3 + 0.6 * rng.random(),
            strength=0.2 + 0.7 * rng.random(),
            affect="negative" if i % 7 == 0 else None,
            created_at=now - timedelta(days=2 + i),
            auto_cues=False,
        )
        if i % 5 == 0:
            engine.update(item.id, content=f"audit{seed}-{i} v2", now=now)
        if i % 9 == 0:
            engine.forget(item.id)
    engine.remember(
        f"audit{seed} ca",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"audit{seed}-c"],
        confidence=0.8,
        auto_cues=False,
    )
    engine.remember(
        f"audit{seed} cb",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"audit{seed}-c"],
        confidence=0.8,
        auto_cues=False,
    )
    return engine


def _run() -> dict:
    metrics = [
        "active", "recycled", "semantic", "episodic", "revised",
        "emotional", "conflicts", "due_now", "avg_retrievability",
        "avg_importance",
    ]
    counts = {m: 0 for m in metrics}
    for seed in range(10):
        engine = _store(seed)
        now = utcnow()
        audit = engine.memory_audit(now=now)
        items = engine.store.all_active()
        stats = engine.backend.stats()
        manual = {
            "active": len(items),
            "recycled": len(engine.backend.list(status=MemoryStatus.RECYCLED)),
            "semantic": stats["semantic"],
            "episodic": stats["episodic"],
            "revised": sum(1 for i in items if i.revision_count > 0),
            "emotional": sum(1 for i in items if i.affect),
            "conflicts": len(engine.consolidator.detect_conflicts()),
            "due_now": len(
                engine.scheduler.due_items(items, now=now, limit=10**6)
            ),
            "avg_retrievability": round(
                sum(engine.curve.retrievability(i, now) for i in items)
                / len(items),
                3,
            ),
            "avg_importance": stats["avg_importance"],
        }
        for m in metrics:
            if m == "avg_retrievability":
                ok = abs(audit[m] - manual[m]) < 0.002
            else:
                ok = audit[m] == manual[m]
            counts[m] += int(ok)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "memory_audit_eval.json"),
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
