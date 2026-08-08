"""Physics-simulate eval (round 246, intuitive physics engine).

10 stores. Each store alternates: with a stored 自由落体定律 memory and
without. physics_simulate must detect the scene, extract quantities,
use the stored law when present (built-in otherwise) and play 4 phases.
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
    if seed % 2 == 0:
        engine.remember(
            "自由落体定律：下落时间≈√(2h/g)，g≈9.8米/秒²",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=SourceType.USER),
            cues=["物理", "定律"],
            importance=0.9,
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    type_ok = qty_ok = law_ok = phases_ok = sim_ok = verdict_ok = (
        advice_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        scene = f"一个球从{10 + seed}米高的地方落下，多久落地？"
        report = engine.physics_simulate(scene)
        type_ok += int("自由落体" in report["types"])
        qty_ok += int(len(report["quantities"]) == 1)
        law_ok += int(
            report["law_used"] is not None
            and (
                report["law_used"]["source"] == "memory"
                if seed % 2 == 0
                else report["law_used"]["source"] == "builtin"
            )
        )
        phases_ok += int(
            len(report["phases"]) == 4
            and [p["phase"] for p in report["phases"]]
            == ["初始状态", "适用规律", "脑内推演", "结果判断"]
        )
        sim_ok += int(
            report["simulation"] is not None and "秒" in report["simulation"]
        )
        verdict_ok += int(report["verdict"] == "ready")
        advice_ok += int(
            ("规律" in report["advice"])
            and ("推演" in report["advice"] or "建议" in report["advice"])
        )
        via_mcp = server._call_tool("physics_simulate", {"scene": scene})
        mcp_ok += int(
            via_mcp["verdict"] == "ready"
            and via_mcp["law_used"] is not None
            and len(via_mcp["phases"]) == 4
        )
    return {
        "stores": 10,
        "type_ok": type_ok,
        "qty_ok": qty_ok,
        "law_ok": law_ok,
        "phases_ok": phases_ok,
        "sim_ok": sim_ok,
        "verdict_ok": verdict_ok,
        "advice_ok": advice_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "physics_simulate_eval.json"),
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
