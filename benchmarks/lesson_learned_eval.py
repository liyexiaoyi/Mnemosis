"""Lesson-learned eval (round 185, schema reuse; Bartlett 1932).

10 stores. Each store: success/failure/lesson/plain memories.
lesson_learned must extract exactly the three experience-tagged memories.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, list[str]]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    ids = []
    for text, cue in (
        (f"上线成功，客户满意{seed}", "ll-1"),
        (f"测试失败，超时严重{seed}", "ll-2"),
        (f"经验：先做原型再开发{seed}", "ll-3"),
        (f"记录了会议纪要{seed}", "ll-4"),
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
    found_ok = tags_ok = preview_ok = skip_ok = empty_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, ids = _store(seed)
        report = engine.lesson_learned(memory_ids=ids)
        found_ok += int(report["total"] == 3)
        tags_ok += int(
            report["tags"] == {"success": 1, "failure": 1, "lesson": 1}
        )
        preview_ok += int(
            all(item["preview"] for item in report["lessons"])
        )
        lesson_ids = {item["id"] for item in report["lessons"]}
        skip_ok += int(ids[3] not in lesson_ids)
        empty_ok += int(MemoryEngine().lesson_learned()["total"] == 0)
        fields_ok += int(
            {"total", "tags", "lessons"} <= set(report)
            and all(
                {"id", "preview", "tag"} <= set(item)
                for item in report["lessons"]
            )
        )
        via_mcp = server._call_tool(
            "lesson_learned", {"memory_ids": ids}
        )
        mcp_ok += int(
            via_mcp["total"] == 3
            and via_mcp["tags"]["success"] == 1
        )
    return {
        "stores": 10,
        "found_ok": found_ok,
        "tags_ok": tags_ok,
        "preview_ok": preview_ok,
        "skip_ok": skip_ok,
        "empty_ok": empty_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "lesson_learned_eval.json"),
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
