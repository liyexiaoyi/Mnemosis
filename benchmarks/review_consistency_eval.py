"""Review-consistency eval (round 248, spaced-review adherence).

10 stores. Each store: one freshly reviewed memory, one overdue memory
and one never-reviewed memory. review_consistency must count them
correctly, report an adherence ratio and a legal verdict.
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
    now = utcnow()
    fresh = engine.remember(
        f"阿丽喜欢城市{seed}。",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["fresh"],
        created_at=now - timedelta(days=30),
        auto_cues=False,
    )
    stale = engine.remember(
        f"阿丽喜欢食物{seed}。",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["stale"],
        created_at=now - timedelta(days=60),
        auto_cues=False,
    )
    engine.remember(
        f"阿丽喜欢颜色{seed}。",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["never"],
        created_at=now - timedelta(days=10),
        auto_cues=False,
    )
    engine.review(fresh.id, success=True, now=now)
    engine.review(fresh.id, success=True, now=now)
    engine.review(stale.id, success=True, now=now - timedelta(days=20))
    engine.review(stale.id, success=True, now=now - timedelta(days=20))
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    counts_ok = on_time_ok = overdue_ok = ratio_ok = verdict_ok = (
        advice_ok
    ) = never_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.review_consistency()
        counts_ok += int(
            report["reviewed_count"]
            == report["on_time_count"] + report["overdue_count"]
            and report["total_memories"]
            == report["reviewed_count"] + report["never_reviewed_count"]
        )
        on_time_ok += int(report["on_time_count"] >= 1)
        overdue_ok += int(report["overdue_count"] >= 1)
        ratio_ok += int(
            abs(
                report["adherence_ratio"]
                - report["on_time_count"] / report["reviewed_count"]
            )
            < 0.001
            and 0 <= report["adherence_ratio"] <= 1
        )
        verdict_ok += int(report["verdict"] in ("high", "medium", "low"))
        advice_ok += int("复习" in report["advice"])
        never_ok += int(report["never_reviewed_count"] >= 1)
        via_mcp = server._call_tool("review_consistency", {})
        mcp_ok += int(
            via_mcp["verdict"] == report["verdict"]
            and via_mcp["reviewed_count"] == report["reviewed_count"]
        )
    return {
        "stores": 10,
        "counts_ok": counts_ok,
        "on_time_ok": on_time_ok,
        "overdue_ok": overdue_ok,
        "ratio_ok": ratio_ok,
        "verdict_ok": verdict_ok,
        "advice_ok": advice_ok,
        "never_ok": never_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "review_consistency_eval.json"
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
