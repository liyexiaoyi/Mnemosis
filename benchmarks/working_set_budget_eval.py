"""Working-set-budget eval (round 210, working-memory limits).

10 stores. Each store has a big engine (9 recently used memories across
3 topics -> overloaded) and a small engine (3 recently used -> light).
working_set_budget must detect both states and recommend chunking.
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
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow  # noqa: E402


def _store(seed: int):
    user = SourceRecord(origin=SourceType.USER)
    big = MemoryEngine()
    for topic in ("物理", "数学", "化学"):
        for i in range(3):
            item = big.remember(
                f"{topic} 知识点 {seed}-{i}",
                kind=MemoryKind.SEMANTIC,
                source=user,
                cues=[topic],
                auto_cues=False,
            )
            item.last_access_at = utcnow()
            big.backend.update(item)
    small = MemoryEngine()
    for i in range(3):
        item = small.remember(
            f"light item {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["light"],
            auto_cues=False,
        )
        item.last_access_at = utcnow()
        small.backend.update(item)
    return big, small, MCPServer(engine=big)


def _run() -> dict:
    big_count_ok = verdict_ok = ratio_ok = chunk_ok = advice_ok = (
        small_ok
    ) = fields_ok = mcp_ok = 0
    for seed in range(10):
        big, small, server = _store(seed)
        report = big.working_set_budget(limit=20)
        big_count_ok += int(report["count"] == 9)
        verdict_ok += int(report["verdict"] == "overloaded")
        ratio_ok += int(report["load_ratio"] == round(9 / 7, 3))
        chunk_ok += int(
            len(report["chunks"]) == 3
            and sum(chunk["count"] for chunk in report["chunks"]) == 9
        )
        advice_ok += int("分批" in report["advice"])
        small_ok += int(small.working_set_budget().get("verdict") == "underutilized")
        fields_ok += int(
            {
                "count",
                "capacity",
                "optimal",
                "load_ratio",
                "verdict",
                "chunks",
                "advice",
            }
            <= set(report)
            and all(
                {"topic", "count", "memory_ids"} <= set(chunk)
                for chunk in report["chunks"]
            )
        )
        via_mcp = server._call_tool(
            "working_set_budget", {"limit": 20}
        )
        mcp_ok += int(
            via_mcp["verdict"] == "overloaded"
            and via_mcp["count"] == 9
            and len(via_mcp["chunks"]) == 3
        )
    return {
        "stores": 10,
        "big_count_ok": big_count_ok,
        "verdict_ok": verdict_ok,
        "ratio_ok": ratio_ok,
        "chunk_ok": chunk_ok,
        "advice_ok": advice_ok,
        "small_ok": small_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "working_set_budget_eval.json"),
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
