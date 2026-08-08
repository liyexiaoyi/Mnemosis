"""Consolidation-forecast eval (round 218, sleep consolidation).

10 stores. Each store: 4 memories with different importance/affect/
strength. consolidation_forecast must rank the weak+emotional+important
one first and list tonight's candidates.
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


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    key = engine.remember(
        f"高数重点 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["数学"],
        importance=0.9,
        affect="negative",
        strength=0.4,
        auto_cues=False,
    )
    engine.remember(
        f"日常笔记 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["笔记"],
        importance=0.6,
        strength=0.8,
        auto_cues=False,
    )
    engine.remember(
        f"获奖 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["荣誉"],
        importance=0.8,
        affect="positive",
        strength=0.95,
        auto_cues=False,
    )
    engine.remember(
        f"琐事 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["琐事"],
        importance=0.2,
        strength=0.9,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine), key


def _run() -> dict:
    total_ok = top_ok = score_ok = gain_ok = reason_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server, key = _store(seed)
        report = engine.consolidation_forecast(limit=4)
        total_ok += int(report["total_memories"] == 4)
        top = report["tonight_candidates"][0]
        top_ok += int(top["id"] == key.id)
        score_ok += int(top["consolidation_score"] >= 0.8)
        gain_ok += int(report["predicted_gain_total"] > 0)
        reason_ok += int(bool(top["reason"]))
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {
                "total_memories",
                "tonight_candidates",
                "predicted_gain_total",
                "advice",
            }
            <= set(report)
            and all(
                {
                    "id",
                    "preview",
                    "importance",
                    "affect",
                    "retrievability",
                    "consolidation_score",
                    "predicted_gain",
                    "reason",
                }
                <= set(item)
                for item in report["tonight_candidates"]
            )
        )
        via_mcp = server._call_tool(
            "consolidation_forecast", {"limit": 4}
        )
        mcp_ok += int(
            len(via_mcp["tonight_candidates"]) == 4
            and via_mcp["tonight_candidates"][0]["id"] == key.id
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "top_ok": top_ok,
        "score_ok": score_ok,
        "gain_ok": gain_ok,
        "reason_ok": reason_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "consolidation_forecast_eval.json"
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
