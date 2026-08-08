"""Sleep-inference eval (round 208, NREM/REM inferential weaving).

10 stores. Each store: two same-topic physics memories decayed into the
consolidation window. sleep_inference must find the pair, rank readiness
and advise letting sleep integrate them.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import timedelta

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    engine.remember(
        f"引力使苹果落地 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        importance=0.7,
        strength=0.5,
        created_at=now - timedelta(days=20),
        auto_cues=False,
    )
    engine.remember(
        f"质量越大引力越大 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        importance=0.7,
        strength=0.5,
        created_at=now - timedelta(days=20),
        auto_cues=False,
    )
    engine.remember(
        f"今日购物清单 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["购物"],
        importance=0.5,
        strength=0.95,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = pair_ok = ready_ok = sort_ok = reason_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.sleep_inference(limit=5)
        total_ok += int(report["total_pairs"] == 1)
        pair_ok += int(
            report["candidates"]
            and report["candidates"][0]["topic"] == "物理"
            and "引力" in report["candidates"][0]["a_preview"]
        )
        ready_ok += int(report["ready_pairs"] == 1)
        sort_ok += int(
            all(
                report["candidates"][i]["readiness"]
                >= report["candidates"][i + 1]["readiness"]
                for i in range(len(report["candidates"]) - 1)
            )
        )
        reason_ok += int(bool(report["candidates"][0]["reason"]))
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {
                "total_pairs",
                "ready_pairs",
                "candidates",
                "advice",
            }
            <= set(report)
            and all(
                {
                    "topic",
                    "a_preview",
                    "b_preview",
                    "shared_cues",
                    "retrievability_a",
                    "retrievability_b",
                    "readiness",
                    "reason",
                }
                <= set(candidate)
                for candidate in report["candidates"]
            )
        )
        via_mcp = server._call_tool("sleep_inference", {})
        mcp_ok += int(
            via_mcp["ready_pairs"] == 1
            and via_mcp["total_pairs"] == 1
            and via_mcp["candidates"][0]["topic"] == "物理"
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "pair_ok": pair_ok,
        "ready_ok": ready_ok,
        "sort_ok": sort_ok,
        "reason_ok": reason_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "sleep_inference_eval.json"),
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
