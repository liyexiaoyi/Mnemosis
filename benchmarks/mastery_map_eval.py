"""Mastery-map eval (round 224, zone of proximal development).

10 stores. Each store: mastered math, developing physics and new music
topics. mastery_map must classify and recommend physics next.
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
    for i in range(2):
        item = engine.remember(
            f"数学题 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["数学"],
            confidence=0.9,
            strength=0.9,
            auto_cues=False,
        )
        item.retrieval_successes = 9
        item.retrieval_failures = 1
        engine.backend.update(item)
    for i in range(2):
        item = engine.remember(
            f"物理题 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            confidence=0.5,
            strength=0.5,
            auto_cues=False,
        )
        item.retrieval_successes = 5
        item.retrieval_failures = 5
        engine.backend.update(item)
    engine.remember(
        f"新音乐知识 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["音乐"],
        confidence=0.3,
        strength=0.4,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    topic_ok = mastered_ok = zpd_ok = new_ok = next_ok = score_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.mastery_map()
        topic_ok += int(len(report["topics"]) == 3)
        by_topic = {topic["topic"]: topic for topic in report["topics"]}
        mastered_ok += int(by_topic["数学"]["flag"] == "mastered")
        zpd_ok += int(by_topic["物理"]["flag"] == "developing")
        new_ok += int(by_topic["音乐"]["flag"] == "new")
        next_ok += int(
            report["next_steps"]
            and report["next_steps"][0]["topic"] == "物理"
        )
        score_ok += int(
            all(0 <= topic["mastery"] <= 1 for topic in report["topics"])
        )
        fields_ok += int(
            {"topics", "next_steps", "advice"} <= set(report)
            and all(
                {
                    "topic",
                    "memory_count",
                    "accuracy",
                    "avg_retrievability",
                    "mastery",
                    "flag",
                }
                <= set(topic)
                for topic in report["topics"]
            )
            and all(
                {"topic", "mastery"} <= set(step)
                for step in report["next_steps"]
            )
        )
        via_mcp = server._call_tool("mastery_map", {})
        mcp_ok += int(
            via_mcp["next_steps"][0]["topic"] == "物理"
            and "developing" in {t["flag"] for t in via_mcp["topics"]}
        )
    return {
        "stores": 10,
        "topic_ok": topic_ok,
        "mastered_ok": mastered_ok,
        "zpd_ok": zpd_ok,
        "new_ok": new_ok,
        "next_ok": next_ok,
        "score_ok": score_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "mastery_map_eval.json"),
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
