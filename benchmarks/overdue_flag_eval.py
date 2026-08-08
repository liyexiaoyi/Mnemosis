"""Overdue-flag eval (round 96, Smolen et al. 2016).

30 memories: 10 overdue (last review 3 days ago, streak 0 -> next review
in the past) and 20 future (freshly reviewed). practice_plan and
practice_forecast should mark the overdue ones and surface them first.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(30):
        item = engine.remember(
            f"逾期测试{i}：条目{i}。",
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[f"条目{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        if i < 10:
            item.last_review_at = now - timedelta(days=3)
        else:
            item.last_review_at = now
        engine.backend.update(item)
    return engine


def _run() -> dict:
    engine = _build_engine()
    now = utcnow()
    overdue_ids = {
        item.id
        for item in engine.store.all_active()
        if item.last_review_at is not None
        and (now - item.last_review_at).total_seconds() > 86400
    }
    plan = engine.practice_plan(limit=30, now=now)
    plan_flagged = sum(
        1 for entry in plan if entry["overdue"] and entry["id"] in overdue_ids
    )
    plan_missing = sum(
        1 for oid in overdue_ids if not any(e["id"] == oid for e in plan)
    )
    forecast = engine.practice_forecast(days=7, now=now)
    fc_by_id = {entry["id"]: entry for entry in forecast}
    fc_overdue = sum(
        1 for oid in overdue_ids if fc_by_id.get(oid, {}).get("overdue")
    )
    fc_sorted = all(
        not b["overdue"] or a["overdue"]
        for a, b in zip(forecast, forecast[1:])
    )
    return {
        "overdue_total": len(overdue_ids),
        "plan_flagged": plan_flagged,
        "plan_missing": plan_missing,
        "forecast_overdue": fc_overdue,
        "forecast_sorted": int(fc_sorted),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "overdue_flag_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["overdue_total"] == 10
        and report["plan_flagged"] == 10
        and report["plan_missing"] == 0
        and report["forecast_overdue"] == 10
        and report["forecast_sorted"] == 1
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
