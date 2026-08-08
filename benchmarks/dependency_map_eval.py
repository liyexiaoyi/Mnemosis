"""Dependency-map eval (round 179, hierarchical planning + CPM).

10 stores. Each store runs the same 6-step plan with declared
dependencies. dependency_map must produce levels, a parallel group, the
critical path and finish level.
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
        {"step": f"写文档{seed}", "depends_on": [1]},
    ]


def _run() -> dict:
    count_ok = dep_ok = level_ok = parallel_ok = critical_ok = finish_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine = MemoryEngine()
        server = MCPServer(engine=engine)
        report = engine.dependency_map(_plan(seed))
        count_ok += int(len(report["steps"]) == 6)
        by_index = {s["index"]: s for s in report["steps"]}
        dep_ok += int(by_index[2]["depends_on"] == [1])
        level_ok += int(
            [s["level"] for s in report["steps"]] == [0, 1, 2, 3, 4, 2]
        )
        parallel_ok += int(
            any(
                group["level"] == 2
                and set(group["step_indices"]) == {2, 5}
                for group in report["parallel_groups"]
            )
        )
        critical_ok += int(
            [s["index"] for s in report["critical_path"]] == [0, 1, 2, 3, 4]
        )
        finish_ok += int(report["finish_level"] == 4)
        fields_ok += int(
            {"steps", "critical_path", "parallel_groups", "finish_level"}
            <= set(report)
            and all(
                {"index", "step", "depends_on", "level"} <= set(s)
                for s in report["steps"]
            )
        )
        via_mcp = server._call_tool(
            "dependency_map", {"plan": _plan(seed)}
        )
        mcp_ok += int(
            len(via_mcp["critical_path"]) == 5
            and via_mcp["finish_level"] == 4
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "dep_ok": dep_ok,
        "level_ok": level_ok,
        "parallel_ok": parallel_ok,
        "critical_ok": critical_ok,
        "finish_ok": finish_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "dependency_map_eval.json"),
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
