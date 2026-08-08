"""Summarize-cluster eval (round 156, Brainerd & Reyna 1990).

10 stores. Each store: 4 memories sharing the cue "工作" and the term
"预算". summarize_cluster must extract shared cues, frequent terms,
evidence and a summary.
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
    for text in (
        f"会议讨论预算方案A{seed}",
        f"会议讨论预算方案B{seed}",
        f"邮件确认预算方案C{seed}",
        f"文档记录预算方案D{seed}",
    ):
        item = engine.remember(
            text,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["工作"],
            auto_cues=False,
        )
        ids.append(item.id)
    return engine, MCPServer(engine=engine), ids


def _run() -> dict:
    found_ok = cues_ok = terms_ok = summary_ok = evidence_ok = fields_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine, server, ids = _store(seed)
        report = engine.summarize_cluster(ids)
        found_ok += int(len(report["memory_ids"]) == 4)
        cues_ok += int("工作" in report["common_cues"])
        terms_ok += int("预算" in report["top_terms"])
        summary_ok += int(
            bool(report["summary"])
            and "4" in report["summary"]
        )
        evidence_ok += int(report["evidence_count"] == 4)
        fields_ok += int(
            {"memory_ids", "summary", "common_cues", "top_terms",
             "evidence_count", "total_chars", "previews"} <= set(report)
            and engine.summarize_cluster(["missing-id"]) is None
        )
        via_mcp = server._call_tool(
            "summarize_cluster", {"memory_ids": ids}
        )
        mcp_ok += int(
            len(via_mcp["memory_ids"]) == 4
            and "预算" in via_mcp["top_terms"]
        )
    return {
        "stores": 10,
        "found_ok": found_ok,
        "cues_ok": cues_ok,
        "terms_ok": terms_ok,
        "summary_ok": summary_ok,
        "evidence_ok": evidence_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "summarize_cluster_eval.json"),
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
