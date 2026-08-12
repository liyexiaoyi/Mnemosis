"""Forgetting-balance eval (round 219, retrieval-induced forgetting).

10 stores. Each store: two physics memories (10 vs 1 accesses) and two
music memories (2 vs 2). forgetting_balance must flag physics, not music.
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


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    hot = engine.remember(
        f"热门物理题 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        auto_cues=False,
    )
    hot.access_count = 10
    engine.backend.update(hot)
    cold = engine.remember(
        f"冷门物理题 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        auto_cues=False,
    )
    cold.access_count = 1
    engine.backend.update(cold)
    for i in range(2):
        item = engine.remember(
            f"音乐曲目 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["音乐"],
            auto_cues=False,
        )
        item.access_count = 2
        engine.backend.update(item)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    topic_ok = flag_ok = imbalanced_ok = balanced_ok = detail_ok = (
        advice_ok
    ) = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.forgetting_balance()
        topic_ok += int(report["total_topics"] == 2)
        flag_ok += int(report["flagged_count"] == 1)
        physics = next(
            topic for topic in report["topics"] if topic["topic"] == "物理"
        )
        imbalanced_ok += int(physics["imbalanced"])
        music = next(
            topic for topic in report["topics"] if topic["topic"] == "音乐"
        )
        balanced_ok += int(not music["imbalanced"])
        detail_ok += int(
            physics["memories"][0]["access_count"] == 10
            and physics["memories"][-1]["access_count"] == 1
            and physics["memories"][0]["share"]
            >= physics["memories"][-1]["share"]
        )
        advice_ok += int("失衡" in report["advice"])
        fields_ok += int(
            {"total_topics", "flagged_count", "topics", "advice"}
            <= set(report)
            and all(
                {"topic", "memories", "imbalanced", "suggestion"}
                <= set(topic)
                for topic in report["topics"]
            )
            and all(
                {"id", "preview", "access_count", "share"}
                <= set(item)
                for topic in report["topics"]
                for item in topic["memories"]
            )
        )
        via_mcp = server._call_tool("forgetting_balance", {})
        mcp_ok += int(
            via_mcp["flagged_count"] == 1
            and next(
                topic for topic in via_mcp["topics"]
                if topic["topic"] == "物理"
            )["imbalanced"]
        )
    return {
        "stores": 10,
        "topic_ok": topic_ok,
        "flag_ok": flag_ok,
        "imbalanced_ok": imbalanced_ok,
        "balanced_ok": balanced_ok,
        "detail_ok": detail_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "forgetting_balance_eval.json"),
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
