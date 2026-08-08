"""Encoding-quality eval (round 150, Craik & Tulving 1975).

10 stores. Each store: one well-encoded memory (cues/context/affect/
importance), one weakly encoded (no cues) and one adequate (one cue +
affect). encoding_quality must score and classify all three and suggest
improvements for the weak one.
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
    good = engine.remember(
        f"今天在办公室完成预算报告，讨论了三个方案{seed}",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["预算", "方案"],
        context="办公室",
        affect="positive",
        importance=0.8,
        strength=0.7,
        auto_cues=False,
    )
    weak = engine.remember(
        "zzz", kind=MemoryKind.EPISODIC, source=user, auto_cues=False
    )
    mid = engine.remember(
        "mid quality memory", kind=MemoryKind.EPISODIC, source=user,
        cues=["中间"], affect="positive", auto_cues=False,
    )
    return engine, MCPServer(engine=engine), good.id


def _run() -> dict:
    high_ok = low_ok = mid_ok = sugg_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, good_id = _store(seed)
        by_content = {
            item.content: item.id for item in engine.store.all_active()
        }
        weak_id = by_content["zzz"]
        mid_id = by_content["mid quality memory"]
        good_q = engine.encoding_quality(good_id)
        weak_q = engine.encoding_quality(weak_id)
        mid_q = engine.encoding_quality(mid_id)
        high_ok += int(
            good_q["score"] >= 80 and good_q["verdict"] == "well_encoded"
        )
        low_ok += int(
            weak_q["score"] < 60 and weak_q["verdict"] == "weak"
        )
        mid_ok += int(
            60 <= mid_q["score"] < 80 and mid_q["verdict"] == "adequate"
        )
        sugg_ok += int(bool(weak_q["suggestions"]))
        fields_ok += int(
            {"memory_id", "score", "verdict", "cue_count", "has_context",
             "has_affect", "importance", "strength", "content_length",
             "suggestions"} <= set(good_q)
            and engine.encoding_quality("missing-id") is None
        )
        via_mcp = server._call_tool(
            "encoding_quality", {"memory_id": good_id}
        )
        mcp_ok += int(via_mcp["verdict"] == "well_encoded")
    return {
        "stores": 10,
        "high_ok": high_ok,
        "low_ok": low_ok,
        "mid_ok": mid_ok,
        "sugg_ok": sugg_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "encoding_quality_eval.json"),
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
