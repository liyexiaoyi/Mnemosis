"""Explain-memory eval (round 151, Koriat & Goldsmith 1996).

10 stores. Each store: one accessed+linked memory, one suppressed memory
and one plain memory. explain_memory must return full state fields,
link/suppression/access facts and None for a missing id.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str, str]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    m1 = engine.remember(
        f"explained one {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"explain-a{seed}"],
        auto_cues=False,
    )
    m2 = engine.remember(
        f"explained two {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"explain-b{seed}"],
        auto_cues=False,
    )
    m3 = engine.remember(
        f"explained three {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"explain-c{seed}"],
        auto_cues=False,
    )
    engine.backend.add_link(m1.id, m3.id)
    engine.backend.add_link(m3.id, m1.id)
    m1.touch()
    m1.touch()
    engine.backend.update(m1)
    engine.suppress_memories([m2.id])
    return engine, MCPServer(engine=engine), m1.id, m2.id


def _run() -> dict:
    found_ok = fields_ok = link_ok = suppress_ok = access_ok = missing_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine, server, m1id, m2id = _store(seed)
        e1 = engine.explain_memory(m1id)
        e2 = engine.explain_memory(m2id)
        found_ok += int(e1 is not None and e2 is not None)
        fields_ok += int(
            {
                "memory_id", "content", "kind", "created_at", "cues",
                "retrievability", "importance", "strength", "confidence",
                "evidence_count", "linked_count", "suppressed",
                "access_count", "last_access_at", "review_streak",
                "last_review_at",
            }
            <= set(e1)
        )
        link_ok += int(e1["linked_count"] >= 1 and e2["linked_count"] == 0)
        suppress_ok += int(e2["suppressed"] and not e1["suppressed"])
        access_ok += int(e1["access_count"] >= 2)
        missing_ok += int(engine.explain_memory("missing-id") is None)
        via_mcp = server._call_tool(
            "explain_memory", {"memory_id": m1id}
        )
        mcp_ok += int(
            via_mcp["access_count"] >= 2 and via_mcp["linked_count"] >= 1
        )
    return {
        "stores": 10,
        "found_ok": found_ok,
        "fields_ok": fields_ok,
        "link_ok": link_ok,
        "suppress_ok": suppress_ok,
        "access_ok": access_ok,
        "missing_ok": missing_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "explain_memory_eval.json"),
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
