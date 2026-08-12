"""Retrieval-snapshot eval (round 243, knowledge tracing / longitudinal).

10 stores. Each store: 3 memories, first snapshot -> strengthen via
successful reviews -> second snapshot with the first as `previous`.
Diff must be present and verdict legal (improving/stable/declining).
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
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    ids = []
    for i in range(3):
        item = engine.remember(
            f"物理公式 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.8,
            strength=0.5,
            created_at=utcnow() - timedelta(days=20),
            auto_cues=False,
        )
        ids.append(item.id)
    return engine, MCPServer(engine=engine), ids


def _run() -> dict:
    fields_ok = first_none_ok = keys_ok = reviewed_ok = verdict_ok = (
        diff_keys_ok
    ) = advice_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, ids = _store(seed)
        first = engine.retrieval_snapshot()
        fields_ok += int(
            {"captured_at", "snapshot", "diff", "advice"} <= set(first)
        )
        first_none_ok += int(first["diff"] is None)
        keys_ok += int(
            {
                "total_memories",
                "avg_retrievability",
                "reviewed_ratio",
                "avg_risk",
                "calibration_score",
                "topics",
            }
            <= set(first["snapshot"])
        )
        for item_id in ids:
            for _ in range(3):
                engine.review(item_id, success=True)
        second = engine.retrieval_snapshot(previous=first)
        reviewed_ok += int(
            second["snapshot"]["reviewed_ratio"]
            > first["snapshot"]["reviewed_ratio"]
        )
        verdict_ok += int(second["diff"]["verdict"] in ("improving", "stable"))
        diff_keys_ok += int(
            {
                "total_memories",
                "avg_retrievability",
                "reviewed_ratio",
                "avg_risk",
                "calibration_score",
                "topics",
                "verdict",
            }
            <= set(second["diff"])
        )
        advice_ok += int("快照" in second["advice"])
        via_mcp = server._call_tool(
            "retrieval_snapshot", {"previous": first}
        )
        mcp_ok += int(
            via_mcp["diff"] is not None
            and via_mcp["diff"].get("verdict") in ("improving", "stable")
        )
    return {
        "stores": 10,
        "fields_ok": fields_ok,
        "first_none_ok": first_none_ok,
        "keys_ok": keys_ok,
        "reviewed_ok": reviewed_ok,
        "verdict_ok": verdict_ok,
        "diff_keys_ok": diff_keys_ok,
        "advice_ok": advice_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "retrieval_snapshot_eval.json"
        ),
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
