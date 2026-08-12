"""Metacog-report eval (round 220, metacognitive calibration).

10 stores. Each store: an overconfident math memory (0.95 confidence,
0.7 accuracy) and an underconfident English memory (0.5 confidence,
0.9 accuracy). metacog_report must flag both and score calibration.
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
    over = engine.remember(
        f"高数公式 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["数学"],
        confidence=0.95,
        auto_cues=False,
    )
    over.retrieval_successes = 7
    over.retrieval_failures = 3
    engine.backend.update(over)
    under = engine.remember(
        f"英语单词 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["英语"],
        confidence=0.5,
        auto_cues=False,
    )
    under.retrieval_successes = 9
    under.retrieval_failures = 1
    engine.backend.update(under)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    topic_ok = over_ok = under_ok = order_ok = score_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.metacog_report()
        topic_ok += int(len(report["topics"]) == 2)
        math = next(
            topic for topic in report["topics"] if topic["topic"] == "数学"
        )
        over_ok += int(
            math["accuracy"] == 0.7
            and math["mean_confidence"] == 0.95
            and math["flag"] == "overconfident"
        )
        english = next(
            topic for topic in report["topics"] if topic["topic"] == "英语"
        )
        under_ok += int(
            english["accuracy"] == 0.9
            and english["flag"] == "underconfident"
        )
        order_ok += int(report["topics"][0]["topic"] == "英语")
        score_ok += int(report["calibration_score"] == 0.675)
        advice_ok += int("过度自信" in report["advice"])
        fields_ok += int(
            {
                "topics",
                "mean_abs_gap",
                "calibration_score",
                "flagged_count",
                "advice",
            }
            <= set(report)
            and all(
                {
                    "topic",
                    "attempts",
                    "accuracy",
                    "mean_confidence",
                    "gap",
                    "flag",
                }
                <= set(topic)
                for topic in report["topics"]
            )
        )
        via_mcp = server._call_tool("metacog_report", {})
        mcp_ok += int(
            via_mcp["flagged_count"] == 2
            and {
                topic["flag"] for topic in via_mcp["topics"]
            } == {"overconfident", "underconfident"}
        )
    return {
        "stores": 10,
        "topic_ok": topic_ok,
        "over_ok": over_ok,
        "under_ok": under_ok,
        "order_ok": order_ok,
        "score_ok": score_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "metacog_report_eval.json"),
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
