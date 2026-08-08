"""Effort-estimate eval (round 186, planning fallacy; Buehler et al.
1994).

10 stores. Each store estimates the same 5-step standard plan:
4+6+8+5+3 = 26 hours, critical path 26, buffered 31.2.
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


def _plan(seed: int) -> list:
    return [
        {"step": f"调研需求{seed}", "depends_on": []},
        {"step": f"设计架构{seed}", "depends_on": [0]},
        {"step": f"开发功能{seed}", "depends_on": [1]},
        {"step": f"测试功能{seed}", "depends_on": [2]},
        {"step": f"部署上线{seed}", "depends_on": [3]},
    ]


def _run() -> dict:
    steps_ok = est_ok = total_ok = cp_ok = buffer_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine = MemoryEngine()
        server = MCPServer(engine=engine)
        report = engine.effort_estimate(_plan(seed))
        steps_ok += int(len(report["steps"]) == 5)
        est_ok += int(
            all(entry["estimated_hours"] > 0 for entry in report["steps"])
        )
        total_ok += int(report["total_hours"] == 26.0)
        cp_ok += int(report["critical_path_hours"] == 26.0)
        buffer_ok += int(report["buffered_total_hours"] == 31.2)
        fields_ok += int(
            {"steps", "total_hours", "critical_path_hours",
             "buffered_total_hours", "note"} <= set(report)
            and bool(report["note"])
            and all(
                {"index", "step", "estimated_hours"} <= set(entry)
                for entry in report["steps"]
            )
        )
        via_mcp = server._call_tool(
            "effort_estimate", {"plan": _plan(seed)}
        )
        mcp_ok += int(
            via_mcp["total_hours"] == 26.0
            and via_mcp["buffered_total_hours"] == 31.2
        )
    return {
        "stores": 10,
        "steps_ok": steps_ok,
        "est_ok": est_ok,
        "total_ok": total_ok,
        "cp_ok": cp_ok,
        "buffer_ok": buffer_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "effort_estimate_eval.json"),
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
