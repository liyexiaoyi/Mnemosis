"""Decision-review eval (round 189, metacognitive monitoring).

10 stores. Each store reviews the same 4-step plan with 2 successes, 1
failure and 1 unknown: success rate 0.5, score 50, verdict fair.
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


def _run() -> dict:
    steps_ok = rate_ok = score_ok = verdict_ok = pattern_ok = lessons_ok = (
        fields_ok
    ) = mcp_ok = 0
    plan = ["调研需求", "设计架构", "开发功能", "测试功能"]
    results = {
        "0": {"status": "success"},
        "1": {"status": "success"},
        "2": {"status": "failure", "note": "超时"},
        "3": {"status": "unknown"},
    }
    for seed in range(10):
        engine = MemoryEngine()
        server = MCPServer(engine=engine)
        report = engine.decision_review(plan, results)
        steps_ok += int(report["total_steps"] == 4)
        rate_ok += int(report["success_rate"] == 0.5)
        score_ok += int(report["score"] == 50)
        verdict_ok += int(report["verdict"] == "fair")
        pattern_ok += int(
            report["patterns"]["success_steps"] == ["调研需求", "设计架构"]
            and report["patterns"]["failure_steps"] == ["开发功能"]
        )
        lessons_ok += int(
            any(
                "开发功能" in lesson["text"]
                for lesson in report["lessons"]
            )
        )
        fields_ok += int(
            {"total_steps", "per_step", "success_rate", "score", "verdict",
             "patterns", "lessons"} <= set(report)
            and all(
                {"index", "step", "status", "note"} <= set(entry)
                for entry in report["per_step"]
            )
        )
        via_mcp = server._call_tool(
            "decision_review", {"plan": plan, "results": results}
        )
        mcp_ok += int(
            via_mcp["score"] == 50 and via_mcp["verdict"] == "fair"
        )
    return {
        "stores": 10,
        "steps_ok": steps_ok,
        "rate_ok": rate_ok,
        "score_ok": score_ok,
        "verdict_ok": verdict_ok,
        "pattern_ok": pattern_ok,
        "lessons_ok": lessons_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "decision_review_eval.json"),
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
