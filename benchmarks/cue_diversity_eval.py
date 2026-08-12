"""Cue-diversity eval (round 233, encoding specificity).

10 stores. Each store: one single-cue, one three-cue, one two-cue memory
and five memories sharing an overloaded cue. cue_diversity must classify
all three levels and flag the overload.
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
    a = engine.remember(
        f"单线索记忆 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["单线"],
        auto_cues=False,
    )
    b = engine.remember(
        f"多线索记忆 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["多线1", "多线2", "多线3"],
        auto_cues=False,
    )
    c = engine.remember(
        f"双线索记忆 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["双线1", "双线2"],
        auto_cues=False,
    )
    crowded = []
    for i in range(5):
        item = engine.remember(
            f"拥挤记忆 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["拥挤"],
            auto_cues=False,
        )
        crowded.append(item)
    return engine, MCPServer(engine=engine), a, b, c, crowded


def _run() -> dict:
    total_ok = fragile_ok = robust_ok = ok_ok = overload_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server, a, b, c, crowded = _store(seed)
        report = engine.cue_diversity()
        total_ok += int(report["total_memories"] == 8)
        by_id = {row["id"]: row for row in report["rows"]}
        fragile_ok += int(by_id[a.id]["level"] == "fragile")
        robust_ok += int(by_id[b.id]["level"] == "robust")
        ok_ok += int(by_id[c.id]["level"] == "ok")
        overload_ok += int(
            "拥挤" in by_id[crowded[0].id]["overloaded_cues"]
        )
        advice_ok += int("脆弱" in report["advice"])
        fields_ok += int(
            {"total_memories", "level_counts", "rows", "advice"}
            <= set(report)
            and all(
                {
                    "id",
                    "preview",
                    "cue_count",
                    "cues",
                    "level",
                    "overloaded_cues",
                    "suggestion",
                }
                <= set(row)
                for row in report["rows"]
            )
        )
        via_mcp = server._call_tool("cue_diversity", {})
        mcp_ok += int(
            via_mcp["total_memories"] == 8
            and "fragile" in via_mcp["level_counts"]
            and "robust" in via_mcp["level_counts"]
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "fragile_ok": fragile_ok,
        "robust_ok": robust_ok,
        "ok_ok": ok_ok,
        "overload_ok": overload_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "cue_diversity_eval.json"),
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
