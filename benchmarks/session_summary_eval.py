"""Session-summary eval (round 161, post-session consolidation).

10 stores. Each store: 2 semantic facts, 2 episodic events and a conflict
pair. session_summary must classify facts/events and flag the conflict.
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
        (f"fact alpha {seed}", "ss-a"),
        (f"fact beta {seed}", "ss-b"),
        (f"event one {seed}", "ss-e1"),
        (f"event two {seed}", "ss-e2"),
        (f"zzz conflict one {seed}", "session-conflict"),
        (f"qqq conflict two {seed}", "session-conflict"),
    ):
        item = engine.remember(
            text,
            kind=(
                MemoryKind.SEMANTIC
                if text.startswith(("fact", "zzz", "qqq"))
                else MemoryKind.EPISODIC
            ),
            source=user,
            cues=[cue],
            confidence=0.8 if cue == "session-conflict" else 1.0,
            auto_cues=False,
        )
        ids.append(item.id)
    return engine, MCPServer(engine=engine), ids


def _run() -> dict:
    total_ok = facts_ok = events_ok = conflict_ok = dup_ok = summary_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server, ids = _store(seed)
        summary = engine.session_summary(ids)
        total_ok += int(summary["total"] == 6)
        facts_ok += int(len(summary["facts"]) == 4)
        events_ok += int(len(summary["events"]) == 2)
        conflict_ok += int(len(summary["conflicts"]) == 1)
        dup_ok += int(len(summary["duplicates"]) == 0)
        summary_ok += int(bool(summary["summary"]))
        fields_ok += int(
            {"total", "facts", "events", "conflicts", "duplicates",
             "summary"} <= set(summary)
            and engine.session_summary(["missing-id"]) is None
        )
        via_mcp = server._call_tool(
            "session_summary", {"memory_ids": ids}
        )
        mcp_ok += int(
            via_mcp["total"] == 6 and len(via_mcp["conflicts"]) == 1
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "facts_ok": facts_ok,
        "events_ok": events_ok,
        "conflict_ok": conflict_ok,
        "dup_ok": dup_ok,
        "summary_ok": summary_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "session_summary_eval.json"),
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
