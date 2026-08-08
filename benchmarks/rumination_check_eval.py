"""Rumination-check eval (round 215, repetitive negative thinking).

10 stores. Each store: one often-accessed negative memory, one rarely
accessed negative memory, one often-accessed positive memory.
rumination_check must flag exactly the risky negative one.
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


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    bad = engine.remember(
        f"答辩搞砸了 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["答辩"],
        affect="negative",
        auto_cues=False,
    )
    bad.access_count = 8
    engine.backend.update(bad)
    minor = engine.remember(
        f"小失误 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["日常"],
        affect="negative",
        auto_cues=False,
    )
    minor.access_count = 2
    engine.backend.update(minor)
    good = engine.remember(
        f"获奖 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["荣誉"],
        affect="positive",
        auto_cues=False,
    )
    good.access_count = 8
    engine.backend.update(good)
    return engine, MCPServer(engine=engine), bad, good


def _run() -> dict:
    neg_ok = risky_ok = flag_ok = positive_ok = topic_ok = risk_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server, bad, good = _store(seed)
        report = engine.rumination_check()
        neg_ok += int(report["negative_count"] == 2)
        risky = report["risky_memories"]
        risky_ok += int(len(risky) == 1)
        flag_ok += int(
            risky and risky[0]["id"] == bad.id and risky[0]["access_count"] == 8
        )
        positive_ok += int(
            good.id not in [item["id"] for item in risky]
        )
        topic_ok += int(
            any(
                topic["topic"] == "答辩"
                and topic["risky_count"] == 1
                for topic in report["rumination_topics"]
            )
        )
        risk_ok += int(report["risk_level"] == "medium")
        fields_ok += int(
            {
                "total_memories",
                "negative_count",
                "risky_memories",
                "rumination_topics",
                "risk_level",
                "advice",
            }
            <= set(report)
            and all(
                {"id", "preview", "affect", "access_count", "topic"}
                <= set(item)
                for item in risky
            )
        )
        via_mcp = server._call_tool("rumination_check", {})
        mcp_ok += int(
            via_mcp["risk_level"] == "medium"
            and len(via_mcp["risky_memories"]) == 1
            and via_mcp["risky_memories"][0]["id"] == bad.id
        )
    return {
        "stores": 10,
        "neg_ok": neg_ok,
        "risky_ok": risky_ok,
        "flag_ok": flag_ok,
        "positive_ok": positive_ok,
        "topic_ok": topic_ok,
        "risk_ok": risk_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "rumination_check_eval.json"),
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
