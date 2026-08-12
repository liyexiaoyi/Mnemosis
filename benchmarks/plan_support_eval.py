"""Plan-support eval (round 177, Baddeley & Hitch 1974).

10 stores. Each store: 2 memories (requirements + go-live checklist) and a
2-step plan. plan_support must retrieve per-step supporting memories.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    engine.remember(
        f"需求文档已确认{seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["需求"],
        auto_cues=False,
    )
    engine.remember(
        f"上线检查清单{seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["上线"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    steps_ok = step1_ok = step2_ok = total_ok = order_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.plan_support(["调研需求", "部署上线"], top_k=3)
        steps_ok += int(len(report["steps"]) == 2)
        step1_ok += int(
            report["steps"][0]["support_count"] >= 1
            and "需求" in report["steps"][0]["support"][0]["preview"]
        )
        step2_ok += int(
            report["steps"][1]["support_count"] >= 1
            and "上线" in report["steps"][1]["support"][0]["preview"]
        )
        total_ok += int(report["total_supported"] == 2)
        order_ok += int(
            all(
                entry["support"][i]["score"]
                >= entry["support"][i + 1]["score"]
                for entry in report["steps"]
                for i in range(len(entry["support"]) - 1)
            )
        )
        fields_ok += int(
            {"steps", "total_supported"} <= set(report)
            and all(
                {"step", "support_count", "support"} <= set(entry)
                and all(
                    {"id", "preview", "score"} <= set(item)
                    for item in entry["support"]
                )
                for entry in report["steps"]
            )
        )
        via_mcp = server._call_tool(
            "plan_support", {"plan": ["调研需求", "部署上线"]}
        )
        mcp_ok += int(
            via_mcp["total_supported"] == 2
            and len(via_mcp["steps"]) == 2
        )
    return {
        "stores": 10,
        "steps_ok": steps_ok,
        "step1_ok": step1_ok,
        "step2_ok": step2_ok,
        "total_ok": total_ok,
        "order_ok": order_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "plan_support_eval.json"),
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
