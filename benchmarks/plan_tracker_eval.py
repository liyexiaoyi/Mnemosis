"""Plan-tracker eval (round 181, goal monitoring).

10 stores. Each store runs a 4-step plan with one done / in_progress /
blocked / pending step. plan_tracker must report statuses, counts and
completion ratio.
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
        f"调研需求{seed}",
        f"设计架构{seed}",
        f"开发功能{seed}",
        f"测试功能{seed}",
    ]


def _run() -> dict:
    total_ok = status_ok = progress_ok = ratio_ok = default_ok = fields_ok = (
        mcp_ok
    ) = 0
    statuses = {
        "0": "done",
        "1": "in_progress",
        "2": "blocked",
        "3": "pending",
    }
    for seed in range(10):
        engine = MemoryEngine()
        server = MCPServer(engine=engine)
        plan = _plan(seed)
        report = engine.plan_tracker(plan, statuses=statuses)
        total_ok += int(report["total"] == 4)
        status_ok += int(
            [s["status"] for s in report["steps"]]
            == ["done", "in_progress", "blocked", "pending"]
        )
        progress_ok += int(
            report["progress"]
            == {"pending": 1, "in_progress": 1, "done": 1, "blocked": 1}
        )
        ratio_ok += int(report["completion_ratio"] == 0.25)
        default_ok += int(
            set(s["status"] for s in engine.plan_tracker(plan)["steps"])
            == {"pending"}
        )
        fields_ok += int(
            {"total", "steps", "progress", "completion_ratio"} <= set(report)
            and all(
                {"index", "step", "status"} <= set(s)
                for s in report["steps"]
            )
        )
        via_mcp = server._call_tool(
            "plan_tracker", {"plan": plan, "statuses": statuses}
        )
        mcp_ok += int(
            via_mcp["completion_ratio"] == 0.25
            and via_mcp["total"] == 4
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "status_ok": status_ok,
        "progress_ok": progress_ok,
        "ratio_ok": ratio_ok,
        "default_ok": default_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "plan_tracker_eval.json"),
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
