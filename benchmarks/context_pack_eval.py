"""Context-pack eval (round 149, Sweller 1988).

10 stores. Each store: memory A reachable via two cues, memories B/C via
one cue each, plus 2 distractors. context_pack(3 queries, budget) must
deduplicate by id, rank by score, respect the character budget and fill
fields.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    engine.remember(
        f"packed alpha {seed} content here",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["pack-a1", "pack-a2"],
        auto_cues=False,
    )
    engine.remember(
        f"packed beta {seed} content here",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["pack-b"],
        auto_cues=False,
    )
    engine.remember(
        f"packed gamma {seed} content here",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["pack-c"],
        auto_cues=False,
    )
    engine.remember(
        f"zzz dist {seed} one",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["dist-1"],
        auto_cues=False,
    )
    engine.remember(
        f"zzz dist {seed} two",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["dist-2"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    found_ok = dedup_ok = order_ok = limit_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        pack = engine.context_pack(
            ["pack-a1", "pack-a2", "pack-b", "pack-c"],
            top_k=2,
            max_chars=100,
        )
        found_ok += int(
            pack["unique_found"] == 3 and pack["query_count"] == 4
        )
        ids = [p["id"] for p in pack["packed"]]
        dedup_ok += int(len(ids) == len(set(ids)))
        order_ok += int(
            all(
                pack["packed"][i]["score"]
                >= pack["packed"][i + 1]["score"]
                for i in range(len(pack["packed"]) - 1)
            )
        )
        limit_ok += int(pack["packed_chars"] <= 100)
        fields_ok += int(
            {"query_count", "total_found", "unique_found", "packed_count",
             "packed_chars", "truncated_count", "packed"} <= set(pack)
            and all(
                {"id", "content", "score"} <= set(p)
                for p in pack["packed"]
            )
        )
        via_mcp = server._call_tool(
            "context_pack",
            {"queries": ["pack-a1", "pack-b", "pack-c"], "max_chars": 100},
        )
        mcp_ok += int(
            via_mcp["unique_found"] == 3
            and via_mcp["packed_chars"] <= 100
        )
    return {
        "stores": 10,
        "found_ok": found_ok,
        "dedup_ok": dedup_ok,
        "order_ok": order_ok,
        "limit_ok": limit_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "context_pack_eval.json"),
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
