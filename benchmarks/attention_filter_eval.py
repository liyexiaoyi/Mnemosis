"""Attention-filter eval (round 225, biased competition).

10 stores. Each store: 2 task-relevant Python memories, a strong
irrelevant shopping memory and a weak-importance travel memory.
attention_filter must keep relevant and suppress only shopping.
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
    engine.remember(
        f"Python 排序算法 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["编程"],
        importance=0.8,
        auto_cues=False,
    )
    engine.remember(
        f"Python 列表操作 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["编程"],
        importance=0.7,
        auto_cues=False,
    )
    shopping = engine.remember(
        f"明天买菜清单 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["买菜"],
        importance=0.8,
        strength=0.9,
        auto_cues=False,
    )
    travel = engine.remember(
        f"旅游照片 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["旅游"],
        importance=0.4,
        strength=0.8,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine), shopping, travel


def _run() -> dict:
    rel_ok = kept_ok = sup_ok = nofalse_ok = detail_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server, shopping, travel = _store(seed)
        report = engine.attention_filter("写Python排序算法", top_k=3)
        rel_ok += int(len(report["relevant"]) >= 1)
        kept_ok += int(report["kept_count"] == len(report["relevant"]))
        suppressed_ids = [item["id"] for item in report["suppressed"]]
        sup_ok += int(shopping.id in suppressed_ids)
        nofalse_ok += int(travel.id not in suppressed_ids)
        detail_ok += int(
            all(
                item["strength"] >= 0.7
                and item["importance"] >= 0.6
                and item["reason"]
                for item in report["suppressed"]
            )
            and all(
                report["suppressed"][i]["strength"]
                >= report["suppressed"][i + 1]["strength"]
                for i in range(len(report["suppressed"]) - 1)
            )
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {
                "task",
                "relevant",
                "kept_count",
                "suppressed",
                "suppressed_count",
                "advice",
            }
            <= set(report)
            and all(
                {"id", "preview", "score"} <= set(item)
                for item in report["relevant"]
            )
            and all(
                {"id", "preview", "strength", "importance", "reason"}
                <= set(item)
                for item in report["suppressed"]
            )
        )
        via_mcp = server._call_tool(
            "attention_filter", {"task": "写Python排序算法", "top_k": 3}
        )
        mcp_ok += int(
            len(via_mcp["relevant"]) >= 1
            and shopping.id
            in [item["id"] for item in via_mcp["suppressed"]]
        )
    return {
        "stores": 10,
        "rel_ok": rel_ok,
        "kept_ok": kept_ok,
        "sup_ok": sup_ok,
        "nofalse_ok": nofalse_ok,
        "detail_ok": detail_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "attention_filter_eval.json"),
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
