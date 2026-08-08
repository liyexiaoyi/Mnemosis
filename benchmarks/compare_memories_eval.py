"""Compare-memories eval (round 154, Johnson et al. 1993).

10 stores. Each store: a duplicate pair, a conflict pair and a distinct
pair. compare_memories must classify all three correctly with overlap and
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

from mnemosis import MemoryEngine  # noqa: E402
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str, str, str, str]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    dup_a = engine.remember(
        f"alpha shared beta value {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["dup-key"],
        auto_cues=False,
    )
    dup_b = engine.remember(
        f"alpha shared beta values {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["dup-key"],
        auto_cues=False,
    )
    con_a = engine.remember(
        f"aaa conflict one {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["conflict-key"],
        auto_cues=False,
    )
    con_b = engine.remember(
        f"bbb conflict two {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["conflict-key"],
        auto_cues=False,
    )
    dis_a = engine.remember(
        f"zzz alpha m {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"dis-a{seed}"],
        auto_cues=False,
    )
    dis_b = engine.remember(
        f"qqq beta n {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"dis-b{seed}"],
        auto_cues=False,
    )
    return (
        engine, MCPServer(engine=engine),
        dup_a.id, dup_b.id, con_a.id, con_b.id, dis_a.id, dis_b.id,
    )


def _run() -> dict:
    dup_ok = conflict_ok = distinct_ok = overlap_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, da, db, ca, cb, sa, sb = _store(seed)
        dup = engine.compare_memories(da, db)
        con = engine.compare_memories(ca, cb)
        dis = engine.compare_memories(sa, sb)
        dup_ok += int(dup["verdict"] == "duplicate")
        conflict_ok += int(
            con["verdict"] == "conflict"
            and "conflict-key" in con["shared_cues"]
        )
        distinct_ok += int(dis["verdict"] == "distinct")
        overlap_ok += int(
            dup["overlap"] >= 0.6 and dis["overlap"] == 0.0
        )
        fields_ok += int(
            {"a", "b", "overlap", "common_terms", "shared_cues", "verdict"}
            <= set(dup)
            and {"id", "preview", "kind", "importance", "confidence",
                 "evidence_count", "created_at"} <= set(dup["a"])
            and engine.compare_memories(da, "missing") is None
        )
        via_mcp = server._call_tool(
            "compare_memories", {"id_a": da, "id_b": db}
        )
        mcp_ok += int(via_mcp["verdict"] == "duplicate")
    return {
        "stores": 10,
        "dup_ok": dup_ok,
        "conflict_ok": conflict_ok,
        "distinct_ok": distinct_ok,
        "overlap_ok": overlap_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "compare_memories_eval.json"),
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
