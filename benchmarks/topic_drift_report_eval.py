"""Topic-drift eval (round 164, Bartlett 1932).

10 stores. Each store: two 30-day periods. Old period: 3 work + 1 life.
New period: 1 work + 2 life + 2 trip. topic_drift_report must compare the
two periods and report shrank/grew/new with correct deltas.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(3):
        engine.remember(
            f"drift work old {seed}-{i}",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["工作"],
            created_at=now - timedelta(days=40, hours=i),
            auto_cues=False,
        )
    engine.remember(
        f"drift life old {seed}",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["生活"],
        created_at=now - timedelta(days=40),
        auto_cues=False,
    )
    engine.remember(
        f"drift work new {seed}",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["工作"],
        created_at=now - timedelta(days=8),
        auto_cues=False,
    )
    for i in range(2):
        engine.remember(
            f"drift life new {seed}-{i}",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["生活"],
            created_at=now - timedelta(days=8, hours=i),
            auto_cues=False,
        )
    for i in range(2):
        engine.remember(
            f"drift trip new {seed}-{i}",
            kind=MemoryKind.EPISODIC,
            source=user,
            cues=["旅行"],
            created_at=now - timedelta(days=8, hours=i),
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    periods_ok = topics_ok = work_ok = life_ok = trip_ok = total_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.topic_drift_report(period_days=30)
        periods_ok += int(len(report["periods"]) == 2)
        by_topic = {t["topic"]: t for t in report["topics"]}
        topics_ok += int(
            {"工作", "生活", "旅行"} <= set(by_topic)
        )
        work_ok += int(
            by_topic["工作"]["old_count"] == 3
            and by_topic["工作"]["new_count"] == 1
            and by_topic["工作"]["delta"] == -2
            and by_topic["工作"]["status"] == "shrank"
        )
        life_ok += int(
            by_topic["生活"]["delta"] == 1
            and by_topic["生活"]["status"] == "grew"
        )
        trip_ok += int(
            by_topic["旅行"]["old_count"] == 0
            and by_topic["旅行"]["delta"] == 2
            and by_topic["旅行"]["status"] == "new"
        )
        total_ok += int(report["total_drift"] == 3)
        fields_ok += int(
            {"periods", "topics", "total_drift"} <= set(report)
            and all(
                {"topic", "old_count", "new_count", "delta", "status"}
                <= set(t)
                for t in report["topics"]
            )
        )
        via_mcp = server._call_tool(
            "topic_drift_report", {"period_days": 30}
        )
        mcp_ok += int(
            via_mcp["total_drift"] == 3
            and len(via_mcp["periods"]) == 2
        )
    return {
        "stores": 10,
        "periods_ok": periods_ok,
        "topics_ok": topics_ok,
        "work_ok": work_ok,
        "life_ok": life_ok,
        "trip_ok": trip_ok,
        "total_ok": total_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "topic_drift_report_eval.json"),
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
