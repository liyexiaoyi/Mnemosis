"""Timeline-report eval (round 135, Conway & Pleydell-Pearce 2000).

10 stores. Each store: 6 episodic memories across 3 days (2 per day) + 1
semantic memory. timeline_report must list only episodes in chronological
order grouped by day, honor a start/end window and fill fields.
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
    now = utcnow().replace(hour=12, minute=0, second=0, microsecond=0)
    for day in range(3):
        for slot in range(2):
            engine.remember(
                f"event {seed} d{day} s{slot}",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=[f"tl{seed}-{day}-{slot}"],
                created_at=(
                    now - timedelta(days=2 - day) + timedelta(hours=slot)
                ),
                auto_cues=False,
            )
    engine.remember(
        f"fact {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        auto_cues=False,
    )
    return engine, now


def _run() -> dict:
    total_ok = days_ok = count_ok = order_ok = range_ok = fields_ok = 0
    for seed in range(10):
        engine, now = _store(seed)
        report = engine.timeline_report()
        total_ok += int(report["total"] == 6)
        days_ok += int(len(report["days"]) == 3)
        count_ok += int(all(d["count"] == 2 for d in report["days"]))
        order_ok += int(
            [d["date"] for d in report["days"]]
            == sorted(d["date"] for d in report["days"])
            and all(
                d["items"][0]["created_at"] <= d["items"][1]["created_at"]
                for d in report["days"]
            )
        )
        window = engine.timeline_report(
            start=now - timedelta(days=1),
            end=now + timedelta(days=1),
        )
        range_ok += int(
            window["total"] == 4 and len(window["days"]) == 2
        )
        fields_ok += int(
            {"total", "days", "start_date", "end_date"} <= set(report)
            and all(
                {"date", "count", "items"} <= set(d)
                and {"id", "preview", "kind", "importance", "created_at"}
                <= set(d["items"][0])
                for d in report["days"]
            )
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "days_ok": days_ok,
        "count_ok": count_ok,
        "order_ok": order_ok,
        "range_ok": range_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "timeline_report_eval.json"),
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
