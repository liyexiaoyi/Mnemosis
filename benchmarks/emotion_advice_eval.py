"""Emotion-advice eval (round 199, Gross 2002).

10 stores. Each store: 8 memories (3 positive, 3 negative incl. 2 on one
topic, 2 neutral). emotion_advice must profile and advise.
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
    for i in range(3):
        engine.remember(
            f"happy memory {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["快乐"],
            affect="positive",
            auto_cues=False,
        )
    engine.remember(
        f"failed launch {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["失败项目"], affect="negative", auto_cues=False,
    )
    engine.remember(
        f"missed deadline {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["失败项目"], affect="negative", auto_cues=False,
    )
    engine.remember(
        f"bad review {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["差评"], affect="negative", auto_cues=False,
    )
    for i in range(2):
        engine.remember(
            f"plain note {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"普通{seed}-{i}"],
            affect="neutral",
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = profile_ok = ratio_ok = flag_ok = advice_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.emotion_advice()
        total_ok += int(report["total_memories"] == 8)
        profile_ok += int(
            report["mood_profile"]
            == {
                "positive": 3,
                "negative": 3,
                "neutral": 2,
                "arousing": 0,
                "mixed": 0,
            }
        )
        ratio_ok += int(report["negative_ratio"] == 0.375)
        flag_ok += int(
            any(
                topic["topic"] == "失败项目"
                and topic["negative_count"] == 2
                for topic in report["flagged_topics"]
            )
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"total_memories", "mood_profile", "negative_ratio",
             "flagged_topics", "advice"} <= set(report)
            and all(
                {"topic", "negative_count"} <= set(topic)
                for topic in report["flagged_topics"]
            )
        )
        via_mcp = server._call_tool("emotion_advice", {})
        mcp_ok += int(
            via_mcp["negative_ratio"] == 0.375
            and via_mcp["mood_profile"]["negative"] == 3
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "profile_ok": profile_ok,
        "ratio_ok": ratio_ok,
        "flag_ok": flag_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "emotion_advice_eval.json"),
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
