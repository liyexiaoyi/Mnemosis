"""Coverage-report eval (round 166, spaced-review coverage).

10 stores. Each store: 3 topic schemas - 甲 (4 memories, 3 reviewed),
乙 (4, 1) and 丙 (2, 0). coverage_report must compute ratios and statuses
per topic.
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

    def _add(topic: str, n: int, reviewed: int) -> None:
        for i in range(n):
            item = engine.remember(
                f"cov {seed} {topic} {i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[topic],
                auto_cues=False,
            )
            if i < reviewed:
                item.retrieval_successes = 1
                engine.backend.update(item)

    _add("主题甲", 4, 3)
    _add("主题乙", 4, 1)
    _add("主题丙", 2, 0)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    topics_ok = a_ok = b_ok = c_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.coverage_report()
        by_topic = {t["topic"]: t for t in report["topics"]}
        topics_ok += int(report["total_topics"] == 3)
        a_ok += int(
            by_topic["主题甲"]["coverage"] == 0.75
            and by_topic["主题甲"]["status"] == "good"
            and by_topic["主题甲"]["reviewed_count"] == 3
        )
        b_ok += int(
            by_topic["主题乙"]["coverage"] == 0.25
            and by_topic["主题乙"]["status"] == "partial"
        )
        c_ok += int(
            by_topic["主题丙"]["coverage"] == 0.0
            and by_topic["主题丙"]["status"] == "unreviewed"
        )
        fields_ok += int(
            {"topics", "total_topics"} <= set(report)
            and all(
                {"topic", "memory_count", "reviewed_count", "coverage",
                 "avg_retrievability", "avg_importance", "status"}
                <= set(t)
                for t in report["topics"]
            )
        )
        via_mcp = server._call_tool("coverage_report", {"limit": 10})
        mcp_ok += int(
            via_mcp["total_topics"] == 3
            and any(
                t["topic"] == "主题丙" and t["status"] == "unreviewed"
                for t in via_mcp["topics"]
            )
        )
    return {
        "stores": 10,
        "topics_ok": topics_ok,
        "a_ok": a_ok,
        "b_ok": b_ok,
        "c_ok": c_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "coverage_report_eval.json"),
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
