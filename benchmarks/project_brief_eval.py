"""Project-brief eval (round 175, schema activation + memory-plan
integration).

10 stores. Each store: background/requirement/risk/plain memories and one
overdue intent. project_brief must assemble background, requirements,
risks and pending actions.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, list[str]]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    ids = []
    for text, cue in (
        (f"项目关于智能客服机器人{seed}", "pb-1"),
        (f"需求：支持中文多轮对话{seed}", "pb-2"),
        (f"风险：模型延迟高{seed}", "pb-3"),
        (f"记录了会议纪要{seed}", "pb-4"),
    ):
        item = engine.remember(
            text,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[cue],
            auto_cues=False,
        )
        ids.append(item.id)
    engine.remember_intent(
        f"交付客服项目{seed}", due_at=utcnow() - timedelta(hours=1)
    )
    return engine, MCPServer(engine=engine), ids


def _run() -> dict:
    bg_ok = req_ok = risk_ok = act_ok = empty_ok = summary_ok = fields_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine, server, ids = _store(seed)
        brief = engine.project_brief("智能客服", memory_ids=ids)
        bg_ok += int(len(brief["background"]) == 4)
        req_ok += int(ids[1] in {r["id"] for r in brief["requirements"]})
        risk_ok += int(ids[2] in {r["id"] for r in brief["risks"]})
        act_ok += int(len(brief["pending_actions"]) >= 1)
        empty_ok += int(
            engine.project_brief("无记忆", memory_ids=["missing-id"])["empty"]
        )
        summary_ok += int(bool(brief["summary"]))
        fields_ok += int(
            {"title", "empty", "background", "requirements", "risks",
             "pending_actions", "summary"} <= set(brief)
            and all(
                {"id", "preview"} <= set(item)
                for item in brief["background"]
            )
        )
        via_mcp = server._call_tool(
            "project_brief", {"title": "智能客服", "memory_ids": ids}
        )
        mcp_ok += int(
            len(via_mcp["background"]) == 4
            and len(via_mcp["pending_actions"]) >= 1
        )
    return {
        "stores": 10,
        "bg_ok": bg_ok,
        "req_ok": req_ok,
        "risk_ok": risk_ok,
        "act_ok": act_ok,
        "empty_ok": empty_ok,
        "summary_ok": summary_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "project_brief_eval.json"),
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
