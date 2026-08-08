"""Life-story eval (round 140, Conway & Pleydell-Pearce 2000).

10 stores. Each store: 9 episodic memories across 3 time periods (30-day
buckets), each period with 3 different themes. life_story must group them
into periods with event counts, themes, importance and highlights.
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
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402

THEMES = ["工作", "生活", "旅行"]


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for offset in (75, 40, 8):
        for slot, theme in enumerate(THEMES):
            engine.remember(
                f"story {seed} {theme} {slot}",
                kind=MemoryKind.EPISODIC,
                source=user,
                cues=[theme],
                importance=0.5 + 0.1 * slot,
                created_at=now - timedelta(days=offset, hours=slot),
                auto_cues=False,
            )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = period_ok = count_ok = theme_ok = highlight_ok = fields_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine, server = _store(seed)
        story = engine.life_story(period_days=30)
        total_ok += int(story["total_events"] == 9)
        period_ok += int(len(story["periods"]) == 3)
        count_ok += int(
            all(p["event_count"] == 3 for p in story["periods"])
        )
        theme_ok += int(
            all(
                {t["cue"] for t in p["top_themes"]} == set(THEMES)
                and all(t["count"] == 1 for t in p["top_themes"])
                for p in story["periods"]
            )
        )
        highlight_ok += int(
            all(
                p["highlights"]
                and p["highlights"][0]["importance"]
                >= p["highlights"][-1]["importance"]
                for p in story["periods"]
            )
        )
        fields_ok += int(
            {"period_days", "total_events", "periods"} <= set(story)
            and all(
                {"period_start", "period_end", "event_count", "top_themes",
                 "avg_importance", "highlights"} <= set(p)
                for p in story["periods"]
            )
        )
        via_mcp = server._call_tool("life_story", {"period_days": 30})
        mcp_ok += int(
            via_mcp["total_events"] == 9
            and len(via_mcp["periods"]) == 3
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "period_ok": period_ok,
        "count_ok": count_ok,
        "theme_ok": theme_ok,
        "highlight_ok": highlight_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "life_story_eval.json"),
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
