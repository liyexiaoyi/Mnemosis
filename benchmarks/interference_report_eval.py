"""Interference-report eval (round 139, Wickens 1972).

10 stores. Each store: 5 memories on cue "会议", 3 on cue "项目" and 2 on
unique cues. interference_report must surface exactly the crowded cues,
in size order, with members and a suggestion.
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(5):
        engine.remember(
            f"meeting alpha {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["会议"],
            auto_cues=False,
        )
    for i in range(3):
        engine.remember(
            f"project beta {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["项目"],
            auto_cues=False,
        )
    engine.remember(
        f"solo gamma {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["唯一"], auto_cues=False,
    )
    engine.remember(
        f"solo delta {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["独有"], auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    cluster_ok = count_ok = min_ok = order_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.interference_report(shared_cue_min=3)
        by_cue = {c["cue"]: c for c in report["crowded_clusters"]}
        cluster_ok += int(
            "会议" in by_cue and "项目" in by_cue
        )
        count_ok += int(
            by_cue["会议"]["memory_count"] == 5
            and by_cue["项目"]["memory_count"] == 3
        )
        min_ok += int(len(report["crowded_clusters"]) == 2)
        order_ok += int(
            report["crowded_clusters"][0]["cue"] == "会议"
        )
        fields_ok += int(
            {"total_cues", "crowded_clusters", "suggestion"} <= set(report)
            and bool(report["suggestion"])
            and all(
                {"cue", "memory_count", "avg_content_overlap", "members"}
                <= set(c)
                and c["members"]
                for c in report["crowded_clusters"]
            )
        )
        via_mcp = server._call_tool(
            "interference_report", {"shared_cue_min": 3}
        )
        mcp_ok += int(
            {c["cue"] for c in via_mcp["crowded_clusters"]}
            == {"会议", "项目"}
        )
    return {
        "stores": 10,
        "cluster_ok": cluster_ok,
        "count_ok": count_ok,
        "min_ok": min_ok,
        "order_ok": order_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "interference_report_eval.json"),
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
