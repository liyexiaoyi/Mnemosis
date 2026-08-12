"""Reasoning-trace eval (round 204, memory-based math/physics reasoning).

10 stores. Each store: a speed fact and a duration fact. reasoning_trace
must recall evidence, extract quantities, build 4 ordered steps, and
store the derived conclusion as an inference memory.
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
from mnemosis.types import (
    MemoryKind,
    SourceRecord,
    SourceType,
)


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    engine.remember(
        f"汽车速度 60 千米每小时 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["速度"],
        auto_cues=False,
    )
    engine.remember(
        f"汽车行驶 3 小时 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["时间"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    evidence_ok = number_ok = step_ok = store_ok = verdict_ok = (
        fields_ok
    ) = mcp_ok = total_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.reasoning_trace(
            "汽车3小时行驶多少千米", topic="物理"
        )
        evidence_ok += int(len(report["evidence_used"]) >= 1)
        number_ok += int(
            any(number["value"] == 3.0 for number in report["numbers"])
            and (
                any(number["value"] == 60.0 for number in report["numbers"])
                or any("60" in item["preview"] for item in report["evidence_used"])
            )
        )
        step_ok += int(
            len(report["steps"]) == 4
            and [step["order"] for step in report["steps"]] == [1, 2, 3, 4]
            and all(step["verdict"] in ("ok", "weak") for step in report["steps"])
        )
        stored_id = report["stored_memory_id"]
        stored = engine.backend.get(stored_id) if stored_id else None
        store_ok += int(
            stored is not None
            and stored.source.origin == SourceType.INFERENCE
            and stored.cues == ["物理"]
        )
        verdict_ok += int(report["verdict"] == "consistent")
        fields_ok += int(
            {
                "problem",
                "topic",
                "evidence_used",
                "numbers",
                "steps",
                "verdict",
                "stored_memory_id",
                "advice",
            }
            <= set(report)
            and all(
                {"id", "preview", "confidence", "score"}
                <= set(item)
                for item in report["evidence_used"]
            )
            and all(
                {"order", "step", "evidence_ids", "verdict"}
                <= set(step)
                for step in report["steps"]
            )
        )
        total_ok += int(
            len(engine.store.all_active()) == 3
        )
        via_mcp = server._call_tool(
            "reasoning_trace",
            {"problem": "汽车3小时行驶多少千米", "topic": "物理"},
        )
        mcp_ok += int(
            bool(via_mcp["stored_memory_id"])
            and len(via_mcp["steps"]) == 4
            and via_mcp["verdict"] == "consistent"
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "evidence_ok": evidence_ok,
        "number_ok": number_ok,
        "step_ok": step_ok,
        "store_ok": store_ok,
        "verdict_ok": verdict_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "reasoning_trace_eval.json"),
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
