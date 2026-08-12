"""Math-ladder eval (round 245, abstraction ladder / math knowledge).

10 stores. Each store alternates: with a stored 速度公式 memory and
without. math_ladder must climb 具体->符号->一般, prefer the stored
formula, fall back to the symbolic template and flag missing numbers.
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
    if seed % 2 == 0:
        engine.remember(
            "速度公式：速度=路程÷时间",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["公式", "速度"],
            importance=0.9,
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    type_ok = concrete_ok = symbolic_ok = general_ok = verdict_ok = (
        ladder_ok
    ) = advice_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.math_ladder(
            "汽车以60千米每小时行驶2小时，路程是多少？"
        )
        type_ok += int("速度" in report["types"])
        concrete_ok += int(len(report["concrete"]["numbers"]) == 2)
        symbolic_ok += int(
            "速度 = 路程 ÷ 时间" in report["symbolic"]["templates"]
        )
        general_ok += int(
            report["general"] is not None
            and (
                report["general"]["source"] == "memory"
                if seed % 2 == 0
                else report["general"]["source"] == "symbolic"
            )
        )
        verdict_ok += int(report["verdict"] == "ready")
        ladder_ok += int(
            len(report["ladder"]) == 3
            and [r["rung"] for r in report["ladder"]]
            == ["具体", "符号", "一般"]
        )
        advice_ok += int(
            ("公式" in report["advice"])
            and ("代入" in report["advice"] or "模板" in report["advice"])
        )
        via_mcp = server._call_tool(
            "math_ladder",
            {"problem": "汽车以60千米每小时行驶2小时，路程是多少？"},
        )
        mcp_ok += int(
            via_mcp["verdict"] == "ready"
            and via_mcp["general"] is not None
        )
    return {
        "stores": 10,
        "type_ok": type_ok,
        "concrete_ok": concrete_ok,
        "symbolic_ok": symbolic_ok,
        "general_ok": general_ok,
        "verdict_ok": verdict_ok,
        "ladder_ok": ladder_ok,
        "advice_ok": advice_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "math_ladder_eval.json"),
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
