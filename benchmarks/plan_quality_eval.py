"""Plan-quality eval (round 174, Miller & Cohen 2001; Newell & Simon
1972).

10 stores. Each store: a project memory + 3 plans (good 5-step Chinese
plan aligned with the memory, weak duplicate plan, empty plan).
plan_quality must score them accordingly.
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
        f"调研需求、架构、开发、测试、部署、上线全部确认{seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["项目"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine), ctx.id


def _run() -> dict:
    good_ok = weak_ok = empty_ok = verb_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, ctx_id = _store(seed)
        good = engine.plan_quality(
            ["调研需求", "设计架构", "开发功能", "测试功能", "部署上线"],
            context_memory_ids=[ctx_id],
        )
        weak = engine.plan_quality(["功能", "功能", "完成"])
        empty = engine.plan_quality([])
        good_ok += int(
            good["score"] >= 75 and good["verdict"] == "good"
        )
        weak_ok += int(
            weak["score"] < 50 and weak["verdict"] == "weak"
            and weak["duplicate_steps"]
        )
        empty_ok += int(
            empty["score"] == 0 and empty["verdict"] == "empty"
        )
        verb_ok += int(good["has_verbs"])
        fields_ok += int(
            {"score", "verdict", "step_count", "has_verbs", "has_ordering",
             "context_alignment", "duplicate_steps", "suggestions"}
            <= set(good)
            and good["step_count"] == 5
        )
        via_mcp = server._call_tool(
            "plan_quality",
            {
                "plan": ["调研需求", "设计架构", "开发功能", "测试功能", "部署上线"],
                "context_memory_ids": [ctx_id],
            },
        )
        mcp_ok += int(
            via_mcp["verdict"] == "good"
            and via_mcp["score"] >= 75
        )
    return {
        "stores": 10,
        "good_ok": good_ok,
        "weak_ok": weak_ok,
        "empty_ok": empty_ok,
        "verb_ok": verb_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "plan_quality_eval.json"),
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
