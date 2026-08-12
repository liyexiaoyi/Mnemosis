"""Intent-register eval (round 129, Einstein & McDaniel 1990).

10 stores. Each store registers 4 intentions (2 due, 1 upcoming, 1 to be
completed). Checks: due list order, report counts, complete/cancel, export
round-trip and record fields.
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

from mnemosis import MemoryEngine
from mnemosis.types import utcnow


def _run() -> dict:
    due_ok = report_ok = complete_ok = cancel_ok = roundtrip_ok = fields_ok = 0
    for seed in range(10):
        engine = MemoryEngine()
        now = utcnow()
        i1 = engine.remember_intent(
            f"task {seed} A", due_at=now - timedelta(hours=1)
        )
        i2 = engine.remember_intent(
            f"task {seed} B", due_at=now - timedelta(hours=2)
        )
        i3 = engine.remember_intent(
            f"task {seed} C", due_at=now + timedelta(days=1),
            context_cue=f"cue{seed}",
        )
        i4 = engine.remember_intent(
            f"task {seed} D", due_at=now - timedelta(hours=3)
        )
        due = engine.intent_due(now=now)
        due_ok += int(
            len(due) == 3
            and [r["id"] for r in due] == [i4["id"], i2["id"], i1["id"]]
        )
        report = engine.intent_report(now=now)
        report_ok += int(
            report["active"] == 4
            and report["overdue"] == 3
            and report["next_upcoming"]["id"] == i3["id"]
        )
        engine.complete_intent(i1["id"], now=now)
        due_after = engine.intent_due(now=now)
        complete_ok += int(
            len(due_after) == 2
            and i1["id"] not in {r["id"] for r in due_after}
        )
        engine.cancel_intent(i3["id"])
        report = engine.intent_report(now=now)
        cancel_ok += int(
            report["active"] == 2
            and report["completed"] == 1
            and report["cancelled"] == 1
        )
        payload = engine.export_memories()
        fresh = MemoryEngine()
        fresh.import_memories(payload)
        roundtrip_ok += int(
            fresh.intent_report(now=now) == report
        )
        fields_ok += int(
            all(
                {
                    "id", "content", "due_at", "context_cue",
                    "importance", "created_at", "status", "completed_at",
                }
                <= set(r)
                for r in engine._intents.values()
            )
        )
    return {
        "stores": 10,
        "due_ok": due_ok,
        "report_ok": report_ok,
        "complete_ok": complete_ok,
        "cancel_ok": cancel_ok,
        "roundtrip_ok": roundtrip_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "intent_register_eval.json"),
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
