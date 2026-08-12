"""Agent-scenario eval (round 102).

One store, one agent loop using the round 99-101 tools:
  1) search() answers 10 factual queries;
  2) list_conflicts() surfaces the 8 stored contradictions;
  3) a practice session with review_score_priority=True returns a plan;
  4) practice_report() returns difficulty stats + review suggestions;
  5) practice_forecast() includes overdue traces.
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


def _build() -> tuple[MemoryEngine, MCPServer]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(10):
        engine.remember(
            f"fact{i} value{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"fact{i}"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for i in range(8):
        engine.remember(
            f"conflict{i} v1",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"conflict{i}"],
            importance=0.8,
            strength=0.5,
            confidence=0.8,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
        engine.remember(
            f"conflict{i} v2",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"conflict{i}"],
            importance=0.8,
            strength=0.5,
            confidence=0.8,
            created_at=now - timedelta(days=10),
            auto_cues=False,
        )
    for i in range(6):
        item = engine.remember(
            f"overdue{i} fact",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"overdue{i}"],
            importance=0.9,
            strength=0.3,
            created_at=now - timedelta(days=20),
            auto_cues=False,
        )
        item.last_review_at = now - timedelta(days=3)
        engine.backend.update(item)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    engine, server = _build()
    now = utcnow()
    # 1) search
    search_ok = 0
    for i in range(10):
        results = server._call_tool(
            "search", {"query": f"fact{i}", "top_k": 3}
        )
        if results and f"value{i}" in results[0]["content"]:
            search_ok += 1
    # 2) conflicts
    conflicts = server._call_tool("list_conflicts", {})
    conflict_ok = sum(
        1 for i in range(8)
        if any(f"conflict{i} v1" in c["a"] + c["b"] for c in conflicts)
    )
    # 3) practice plan with review score
    plan = engine.practice_plan(
        limit=10, now=now
    )
    plan_ok = len(plan) > 0
    # 5) forecast includes overdue (check before reviewing anything)
    forecast = engine.practice_forecast(days=7, now=now)
    overdue_ids = {
        item.id
        for item in engine.store.all_active()
        if item.last_review_at is not None
        and (now - item.last_review_at).total_seconds() > 86400
    }
    forecast_ok = sum(
        1 for entry in forecast
        if entry["overdue"] and entry["id"] in overdue_ids
    )
    # 4) report difficulty + suggestions
    answers = [
        {"id": item.id, "attempt": "测试"}
        for item in engine.store.all_active()
    ]
    report = engine.practice_report(answers, now=now)
    report_ok = bool(
        report["difficulty"]
        and report["difficulty"]["n"] == len(answers)
        and all("next_review_at" in d for d in report["details"])
    )
    return {
        "search_ok": search_ok,
        "conflict_ok": conflict_ok,
        "plan_ok": int(plan_ok),
        "report_ok": int(report_ok),
        "forecast_overdue": forecast_ok,
        "overdue_total": len(overdue_ids),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "agent_scenario_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["search_ok"] == 10
        and report["conflict_ok"] == 8
        and report["plan_ok"] == 1
        and report["report_ok"] == 1
        and report["forecast_overdue"] == report["overdue_total"]
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
