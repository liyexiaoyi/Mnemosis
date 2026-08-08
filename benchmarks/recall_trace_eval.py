"""Recall-trace eval (round 194, metacognitive explanation).

10 stores. Each store: 3 memories (1 target + 2 distractors). recall_trace
must explain the top hit with scanned count and reasons.
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
    m1 = engine.remember(
        f"trace target memory {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["trace-key"],
        auto_cues=False,
    )
    engine.remember(
        f"trace distractor one {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"trace-d1{seed}"],
        auto_cues=False,
    )
    engine.remember(
        f"trace distractor two {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"trace-d2{seed}"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine), m1.id


def _run() -> dict:
    scanned_ok = hit_ok = reasons_ok = summary_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, m1id = _store(seed)
        trace = engine.recall_trace("trace-key", top_k=3)
        scanned_ok += int(trace["candidates_scanned"] == 3)
        hit_ok += int(trace["results"][0]["id"] == m1id)
        reasons_ok += int(
            any(
                "overlap" in reason
                for reason in trace["results"][0]["reasons"]
            )
            and trace["results"][0]["confident"]
        )
        summary_ok += int(bool(trace["top_reason_summary"]))
        fields_ok += int(
            {"query", "candidates_scanned", "results",
             "top_reason_summary"} <= set(trace)
            and all(
                {"id", "preview", "score", "confident", "reasons"}
                <= set(result)
                for result in trace["results"]
            )
        )
        via_mcp = server._call_tool(
            "recall_trace", {"query": "trace-key", "top_k": 3}
        )
        mcp_ok += int(
            via_mcp["results"][0]["id"] == m1id
            and via_mcp["candidates_scanned"] == 3
        )
    return {
        "stores": 10,
        "scanned_ok": scanned_ok,
        "hit_ok": hit_ok,
        "reasons_ok": reasons_ok,
        "summary_ok": summary_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "recall_trace_eval.json"),
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
