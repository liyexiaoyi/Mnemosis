"""Retrieval-quality eval (round 191, metacognitive monitoring).

10 stores. Each store: 4 memories with cues + 2 missing queries.
retrieval_quality must report 4 hits, 2 weak, hit rate 0.667 and verdict
fair.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(4):
        engine.remember(
            f"quality item {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"rq-{seed}-{i}"],
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    eval_ok = hit_ok = weak_ok = rate_ok = verdict_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        queries = [
            f"rq-{seed}-0", f"rq-{seed}-1", f"rq-{seed}-2",
            f"rq-{seed}-3", "zzz miss", "qqq miss",
        ]
        report = engine.retrieval_quality(queries=queries, top_k=3)
        eval_ok += int(report["queries_evaluated"] == 6)
        hit_ok += int(report["hit_count"] == 4)
        weak_ok += int(report["weak_count"] == 2)
        rate_ok += int(report["hit_rate"] == 0.667)
        verdict_ok += int(report["verdict"] == "fair")
        fields_ok += int(
            {"queries_evaluated", "hit_count", "weak_count",
             "avg_top_score", "avg_top_retrievability", "hit_rate",
             "weak_rate", "verdict"} <= set(report)
            and 0.0 <= report["avg_top_score"] <= 1.0
        )
        via_mcp = server._call_tool(
            "retrieval_quality", {"queries": queries, "top_k": 3}
        )
        mcp_ok += int(
            via_mcp["queries_evaluated"] == 6
            and via_mcp["hit_count"] == 4
        )
    return {
        "stores": 10,
        "eval_ok": eval_ok,
        "hit_ok": hit_ok,
        "weak_ok": weak_ok,
        "rate_ok": rate_ok,
        "verdict_ok": verdict_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "retrieval_quality_eval.json"),
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
