"""MCP cloud integration eval (round 37).

Drives Mnemosis through its real MCP JSON-RPC tools (plan / record_outcome
/ recall / check) with qwen3.7-plus acting as the agent: plan for a goal by
reusing a reference project, record an execution outcome, then judge a
follow-up question and a never-seen question (gap -> unknown).
"""

from __future__ import annotations

import json
import os
import re
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType

REFERENCE_STEPS = [
    "阿丽在2026年4月1日订了去京都的机票。",
    "阿丽在2026年4月2日买了相机。",
    "阿丽在2026年4月3日收拾了行李。",
    "阿丽在2026年4月4日去了京都。",
]
PLAN_GOAL = "大壮想去京都旅行，参考阿丽是怎么准备的？"
PLAN_KEYS = ["机票", "相机", "行李", "京都"]


def _cloud(prompt: str) -> str:
    from cloud_qwen_matrix import cloud_generate

    return cloud_generate(prompt, max_tokens=300)


def _build_server() -> MCPServer:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for step in REFERENCE_STEPS:
        cue = re.split(r"[在]", step, maxsplit=1)[0]
        engine.remember(
            step,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[cue],
        )
    return MCPServer(engine=engine)


def _ordered(contents: list[str]) -> bool:
    idx = [contents.index(s) for s in REFERENCE_STEPS if s in contents]
    return bool(idx and idx == sorted(idx) and len(idx) == len(REFERENCE_STEPS))


def main() -> int:
    server = _build_server()
    report: dict = {}

    # 1) plan tool
    plan_result = server._call_tool("plan", {"goal": PLAN_GOAL, "top_k": 8})
    plan_contents = [r["content"] for r in plan_result]
    report["plan_ordered"] = int(_ordered(plan_contents))
    report["plan_all_steps"] = int(
        all(s in plan_contents for s in REFERENCE_STEPS)
    )
    plan_answer = _cloud(
        "下面是记忆上下文。请为问题中的目标写一个按时间顺序的步骤计划，"
        "每步一行。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in plan_contents)
        + f"\n\n目标：{PLAN_GOAL}"
    )
    report["agent_plan_coverage"] = int(
        all(k in plan_answer for k in PLAN_KEYS)
    )
    print("plan ordered:", report["plan_ordered"],
          "all_steps:", report["plan_all_steps"],
          "agent_coverage:", report["agent_plan_coverage"], flush=True)

    # 2) record_outcome tool
    outcome = server._call_tool(
        "record_outcome",
        {
            "goal": "大壮京都旅行",
            "step": "订机票",
            "success": False,
            "note": "航班取消",
        },
    )
    report["outcome_recorded"] = int("失败" in outcome["content"])
    print("outcome recorded:", report["outcome_recorded"], flush=True)

    # 3) recall + agent judges which step failed
    recall_result = server._call_tool(
        "recall", {"query": "大壮京都旅行计划中哪一步出了问题？", "top_k": 5}
    )
    recall_contents = [r["content"] for r in recall_result]
    judge_answer = _cloud(
        "只用下面的记忆上下文回答；没有就答unknown。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in recall_contents)
        + "\n\n问题：大壮京都旅行计划中哪一步出了问题？"
    )
    report["agent_judge_outcome"] = int("订机票" in judge_answer)
    print("judge outcome:", report["agent_judge_outcome"], flush=True)

    # 4) check tool + gap -> unknown
    check = server._call_tool("check", {"query": "阿丽上次旅行顺利吗？", "top_k": 3})
    gap_answer = _cloud(
        "只用下面的记忆上下文回答；没有就答unknown。\n\n"
        "上下文：\n" + "\n".join(f"- {i['content']}" for i in check["items"])
        + "\n\n问题：阿丽上次旅行顺利吗？"
    )
    report["agent_gap_unknown"] = int("unknown" in gap_answer.lower())
    report["check_gaps"] = check["gaps"]
    print("gap unknown:", report["agent_gap_unknown"],
          "gaps:", check["gaps"], flush=True)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    out = os.path.join(_BENCH, "results", "mcp_cloud_eval.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
