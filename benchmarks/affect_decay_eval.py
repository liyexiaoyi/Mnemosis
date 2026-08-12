"""Affect-decay eval (round 239, emotion regulation).

10 stores. Each store: one persistent negative (streak 0), one fading
positive (streak 2) and one processed negative (streak 3).
affect_decay must classify all three and advise reappraisal.
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
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    persistent = engine.remember(
        f"答辩搞砸了 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["答辩"],
        affect="negative",
        auto_cues=False,
    )
    persistent.review_streak = 0
    engine.backend.update(persistent)
    fading = engine.remember(
        f"获奖 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["荣誉"],
        affect="positive",
        auto_cues=False,
    )
    fading.review_streak = 2
    engine.backend.update(fading)
    processed = engine.remember(
        f"小失误 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["日常"],
        affect="negative",
        auto_cues=False,
    )
    processed.review_streak = 3
    engine.backend.update(processed)
    return engine, MCPServer(engine=engine), persistent, fading, processed


def _run() -> dict:
    total_ok = persistent_ok = fading_ok = processed_ok = counts_ok = (
        advice_ok
    ) = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, persistent, fading, processed = _store(seed)
        report = engine.affect_decay()
        total_ok += int(report["total_emotional"] == 3)
        by_id = {row["id"]: row for row in report["rows"]}
        persistent_ok += int(
            by_id[persistent.id]["status"] == "persistent"
            and by_id[persistent.id]["charge"] == 1.0
            and by_id[persistent.id]["persistence_days"] == 30.0
        )
        fading_ok += int(
            by_id[fading.id]["status"] == "fading"
            and by_id[fading.id]["charge"] == round(1 / 3, 3)
        )
        processed_ok += int(
            by_id[processed.id]["status"] == "processed"
            and by_id[processed.id]["charge"] == 0.0
        )
        counts_ok += int(
            report["status_counts"]
            == {"persistent": 1, "fading": 1, "processed": 1}
        )
        advice_ok += int("重评" in report["advice"])
        fields_ok += int(
            {"total_emotional", "status_counts", "rows", "advice"}
            <= set(report)
            and all(
                {
                    "id",
                    "preview",
                    "affect",
                    "review_streak",
                    "charge",
                    "persistence_days",
                    "status",
                    "hint",
                }
                <= set(row)
                for row in report["rows"]
            )
        )
        via_mcp = server._call_tool("affect_decay", {})
        mcp_ok += int(
            via_mcp["total_emotional"] == 3
            and "persistent" in via_mcp["status_counts"]
            and "processed" in via_mcp["status_counts"]
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "persistent_ok": persistent_ok,
        "fading_ok": fading_ok,
        "processed_ok": processed_ok,
        "counts_ok": counts_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "affect_decay_eval.json"),
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
