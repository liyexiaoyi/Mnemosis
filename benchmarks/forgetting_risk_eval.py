"""Forgetting-risk eval (round 170, forgetting-curve scheduling).

10 stores. Each store: 2 old high-importance memories + 2 new trivial
ones. forgetting_risk must rank the old important ones first with correct
risk values.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    for i in range(2):
        engine.remember(
            f"old important {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"fr-oi{seed}-{i}"],
            importance=0.9,
            created_at=now - timedelta(days=30),
            auto_cues=False,
        )
    for i in range(2):
        engine.remember(
            f"new trivial {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"fr-nt{seed}-{i}"],
            importance=0.2,
            created_at=now - timedelta(days=1),
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = order_ok = top_ok = risk_ok = avg_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.forgetting_risk(now=utcnow())
        total_ok += int(report["total"] == 4)
        order_ok += int(
            all(
                report["riskiest"][i]["risk"]
                >= report["riskiest"][i + 1]["risk"]
                for i in range(len(report["riskiest"]) - 1)
            )
        )
        top_ok += int(report["riskiest"][0]["importance"] == 0.9)
        risk_ok += int(
            all(
                entry["risk"]
                == round(
                    entry["importance"]
                    * (1 - entry["retrievability"]),
                    3,
                )
                for entry in report["riskiest"]
            )
        )
        avg_ok += int(report["avg_risk"] > 0.0)
        fields_ok += int(
            {"total", "avg_risk", "riskiest"} <= set(report)
            and all(
                {"id", "preview", "importance", "retrievability", "risk"}
                <= set(entry)
                for entry in report["riskiest"]
            )
        )
        via_mcp = server._call_tool("forgetting_risk", {"limit": 5})
        mcp_ok += int(
            via_mcp["total"] == 4
            and via_mcp["riskiest"][0]["importance"] == 0.9
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "order_ok": order_ok,
        "top_ok": top_ok,
        "risk_ok": risk_ok,
        "avg_ok": avg_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "forgetting_risk_eval.json"),
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
