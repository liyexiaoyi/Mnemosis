"""Review-load eval (round 116).

10 varied stores (due/overdue/weak/fresh mixes). review_load() should
match manual computation for due_now, overdue, weak and the load index.
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
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    rng = random.Random(seed)
    for i in range(25):
        item = engine.remember(
            f"load{seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"load{seed}-{i}"],
            importance=0.5,
            strength=0.15 + 0.8 * rng.random(),
            created_at=now - timedelta(days=rng.randint(1, 40)),
            auto_cues=False,
        )
        if rng.random() < 0.4:
            item.last_review_at = now - timedelta(days=rng.randint(2, 5))
            engine.backend.update(item)
    return engine


def _run() -> dict:
    metrics = ["due_now", "overdue", "weak", "load_index"]
    counts = {m: 0 for m in metrics}
    for seed in range(10):
        engine = _store(seed)
        now = utcnow()
        load = engine.review_load(days=7, now=now)
        items = engine.store.all_active()
        manual_due = len(
            engine.scheduler.due_items(items, now=now, limit=10**6)
        )
        manual_overdue = 0
        manual_weak = 0
        manual_soon = 0
        horizon = now + timedelta(days=7)
        for item in items:
            if engine.curve.retrievability(item, now) < 0.3:
                manual_weak += 1
            nxt = engine.scheduler.next_review_at(item, now)
            if nxt <= horizon:
                manual_soon += 1
            if nxt < now:
                manual_overdue += 1
        counts["due_now"] += int(load["due_now"] == manual_due)
        counts["overdue"] += int(load["overdue"] == manual_overdue)
        counts["weak"] += int(load["weak"] == manual_weak)
        counts["load_index"] += int(
            load["load_index"] == manual_soon + manual_overdue
        )
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "review_load_eval.json"),
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
