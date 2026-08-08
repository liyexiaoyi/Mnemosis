"""Analogy-bridge eval (round 228, structure mapping).

10 stores. Each store: astronomy and physics memories sharing a
"revolve around" relation, plus an unrelated shopping memory.
analogy_bridge must bridge astronomy-physics and skip shopping.
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
    engine.remember(
        f"行星绕太阳转 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["天文"],
        auto_cues=False,
    )
    engine.remember(
        f"电子绕原子核转 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        auto_cues=False,
    )
    engine.remember(
        f"买牛奶面包 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["购物"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    scan_ok = count_ok = pair_ok = score_ok = nofalse_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.analogy_bridge(min_structure=0.2, limit=5)
        scan_ok += int(report["total_pairs_scanned"] == 3)
        count_ok += int(report["analogy_count"] >= 1)
        top = report["analogies"][0]
        pair_ok += int(
            {top["topic_a"], top["topic_b"]} == {"天文", "物理"}
        )
        score_ok += int(top["structure_score"] >= 0.2)
        nofalse_ok += int(
            "买牛奶面包"
            not in [analogy["a_preview"] for analogy in report["analogies"]]
            and "买牛奶面包"
            not in [analogy["b_preview"] for analogy in report["analogies"]]
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"total_pairs_scanned", "analogy_count", "analogies", "advice"}
            <= set(report)
            and all(
                {
                    "topic_a",
                    "topic_b",
                    "a_preview",
                    "b_preview",
                    "structure_score",
                    "suggestion",
                }
                <= set(analogy)
                for analogy in report["analogies"]
            )
        )
        via_mcp = server._call_tool(
            "analogy_bridge", {"min_structure": 0.2, "limit": 5}
        )
        mcp_ok += int(
            via_mcp["analogy_count"] >= 1
            and {via_mcp["analogies"][0]["topic_a"],
                 via_mcp["analogies"][0]["topic_b"]}
            == {"天文", "物理"}
        )
    return {
        "stores": 10,
        "scan_ok": scan_ok,
        "count_ok": count_ok,
        "pair_ok": pair_ok,
        "score_ok": score_ok,
        "nofalse_ok": nofalse_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "analogy_bridge_eval.json"),
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
