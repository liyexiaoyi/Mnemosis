"""Numeric-reasoning eval (round 176, Dehaene 1997; Johnson-Laird 1983).

10 stores. Each store: a speed fact + 4 problems (consistent, unit-mix,
division-by-zero, Chinese-number). numeric_reasoning must extract numbers
and flag issues.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    ctx = engine.remember(
        f"汽车速度 {60 + seed} 千米每小时",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["速度"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine), ctx.id


def _run() -> dict:
    consistent_ok = mixed_ok = zero_ok = numbers_ok = zhnum_ok = fields_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine, server, ctx_id = _store(seed)
        speed = 60 + seed
        consistent = engine.numeric_reasoning(
            f"汽车3小时行驶{speed * 3}千米",
            context_memory_ids=[ctx_id],
        )
        consistent_ok += int(
            consistent["verdict"] == "consistent"
            and any(
                check["type"] == "memory_consistency" and check["ok"]
                for check in consistent["checks"]
            )
        )
        mixed = engine.numeric_reasoning("绳子长2米，又接上3公里")
        mixed_ok += int(
            mixed["verdict"] == "review_needed"
            and any(check["type"] == "unit_mix" for check in mixed["checks"])
        )
        zero = engine.numeric_reasoning("把10元除以0个人")
        zero_ok += int(
            zero["verdict"] == "review_needed"
            and any(
                check["type"] == "zero_division" for check in zero["checks"]
            )
        )
        numbers_ok += int(
            [entry["value"] for entry in consistent["numbers"]]
            == [3.0, float(speed * 3)]
        )
        zh = engine.numeric_reasoning("一百元买3个苹果")
        zhnum_ok += int(bool(zh["chinese_numbers"]))
        fields_ok += int(
            {"numbers", "chinese_numbers", "checks", "verdict"}
            <= set(consistent)
            and all(
                {"type", "message", "ok"} <= set(check)
                for check in consistent["checks"]
            )
        )
        via_mcp = server._call_tool(
            "numeric_reasoning",
            {
                "problem": f"汽车3小时行驶{speed * 3}千米",
                "context_memory_ids": [ctx_id],
            },
        )
        mcp_ok += int(via_mcp["verdict"] == "consistent")
    return {
        "stores": 10,
        "consistent_ok": consistent_ok,
        "mixed_ok": mixed_ok,
        "zero_ok": zero_ok,
        "numbers_ok": numbers_ok,
        "zhnum_ok": zhnum_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "numeric_reasoning_eval.json"),
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
