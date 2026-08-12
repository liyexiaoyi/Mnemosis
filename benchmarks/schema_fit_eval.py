"""Schema-fit eval (round 209, schema-based consolidation).

10 stores. Each store: 3 same-topic physics memories (schema) + 1 music
memory. schema_fit must label physics as assimilate and music as
accommodate, summarize schemas and advise.
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
    for content in (f"物理公式A {seed}", f"物理公式B {seed}", f"物理实验C {seed}"):
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            auto_cues=False,
        )
    engine.remember(
        f"贝多芬交响曲 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["音乐"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = schema_ok = assim_ok = accom_ok = summary_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.schema_fit()
        total_ok += int(report["total_memories"] == 4)
        schema_ok += int(report["schema_count"] == 1)
        assim_ok += int(
            all(
                row["verdict"] == "assimilate" and row["best_schema"] == "物理"
                for row in report["rows"]
                if row["topic"] == "物理"
            )
        )
        music_row = next(
            row for row in report["rows"] if row["topic"] == "音乐"
        )
        accom_ok += int(music_row["verdict"] == "accommodate")
        physics = next(
            schema for schema in report["schema_summary"]
            if schema["topic"] == "物理"
        )
        summary_ok += int(
            physics["member_count"] == 3
            and physics["avg_fit"] > 0.5
            and physics["assimilate"] == 3
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {
                "total_memories",
                "schema_count",
                "rows",
                "verdict_counts",
                "schema_summary",
                "advice",
            }
            <= set(report)
            and all(
                {"id", "preview", "topic", "best_schema", "fit", "verdict"}
                <= set(row)
                for row in report["rows"]
            )
        )
        via_mcp = server._call_tool("schema_fit", {})
        mcp_ok += int(
            via_mcp["schema_count"] == 1
            and via_mcp["verdict_counts"].get("assimilate", 0) == 3
            and via_mcp["verdict_counts"].get("accommodate", 0) == 1
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "schema_ok": schema_ok,
        "assim_ok": assim_ok,
        "accom_ok": accom_ok,
        "summary_ok": summary_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "schema_fit_eval.json"),
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
