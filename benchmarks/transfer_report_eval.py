"""Transfer-report eval (round 190, schema reuse; Bartlett 1932).

10 stores. Each store: 3 lesson memories (2 matching plan steps, 1 not)
and a 3-step plan. transfer_report must map the applicable lessons.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, list[str]]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    ids = []
    for text, cue in (
        (f"成功：先调研需求再开发{seed}", "tr-1"),
        (f"失败：测试超时{seed}", "tr-2"),
        (f"经验：原型先行{seed}", "tr-3"),
    ):
        item = engine.remember(
            text,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[cue],
            auto_cues=False,
        )
        ids.append(item.id)
    return engine, MCPServer(engine=engine), ids


def _run() -> dict:
    steps_ok = total_ok = match_ok = hit_ok = skip_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, ids = _store(seed)
        report = engine.transfer_report(
            ["调研需求", "开发功能", "测试功能"],
            lessons_memory_ids=ids,
        )
        steps_ok += int(len(report["plan_steps"]) == 3)
        total_ok += int(report["total_lessons"] == 3)
        match_ok += int(len(report["applicable_lessons"]) == 2)
        by_id = {
            lesson["id"]: lesson for lesson in report["applicable_lessons"]
        }
        hit_ok += int(
            "调研需求" in by_id[ids[0]]["matched_steps"]
            and "测试功能" in by_id[ids[1]]["matched_steps"]
        )
        skip_ok += int(ids[2] not in by_id)
        fields_ok += int(
            {"plan_steps", "total_lessons", "applicable_lessons",
             "suggestion"} <= set(report)
            and bool(report["suggestion"])
            and all(
                {"id", "preview", "tag", "matched_steps"} <= set(lesson)
                for lesson in report["applicable_lessons"]
            )
        )
        via_mcp = server._call_tool(
            "transfer_report",
            {"plan": ["调研需求", "开发功能", "测试功能"],
             "lessons_memory_ids": ids},
        )
        mcp_ok += int(len(via_mcp["applicable_lessons"]) == 2)
    return {
        "stores": 10,
        "steps_ok": steps_ok,
        "total_ok": total_ok,
        "match_ok": match_ok,
        "hit_ok": hit_ok,
        "skip_ok": skip_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "transfer_report_eval.json"),
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
