"""KG-export eval (round 145, Collins & Quillian 1969).

10 stores. Each store: a hand-linked hub+5 nodes and 2 isolated memories.
kg_export must return all nodes, deduplicated undirected edges, counts
and well-formed node/edge fields.
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
    hub = engine.remember(
        f"zzz hub {seed}.", kind=MemoryKind.SEMANTIC, source=user
    )
    nodes = [
        engine.remember(
            f"qqq nod {letter}.", kind=MemoryKind.SEMANTIC, source=user
        )
        for letter in ("x", "y", "z", "u", "v")
    ]
    for node in nodes:
        engine.backend.add_link(hub.id, node.id)
    engine.remember("aaa lon m.", kind=MemoryKind.SEMANTIC, source=user)
    engine.remember("aaa lon n.", kind=MemoryKind.SEMANTIC, source=user)
    return engine, MCPServer(engine=engine), hub.id


def _run() -> dict:
    node_ok = edge_ok = dedup_ok = fields_ok = count_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, hubid = _store(seed)
        graph = engine.kg_export()
        node_ok += int(graph["node_count"] == 8)
        edge_ok += int(graph["edge_count"] == 5)
        pairs = {
            frozenset((e["source"], e["target"])) for e in graph["edges"]
        }
        dedup_ok += int(len(pairs) == len(graph["edges"]) == 5)
        fields_ok += int(
            {"nodes", "edges", "node_count", "edge_count"} <= set(graph)
            and all(
                {"id", "label", "kind"} <= set(n) for n in graph["nodes"]
            )
            and all(
                {"source", "target", "weight"} <= set(e)
                for e in graph["edges"]
            )
        )
        count_ok += int(
            graph["node_count"] == len(graph["nodes"])
            and graph["edge_count"] == len(graph["edges"])
            and hubid in {n["id"] for n in graph["nodes"]}
        )
        via_mcp = server._call_tool("kg_export", {})
        mcp_ok += int(
            via_mcp["node_count"] == 8 and via_mcp["edge_count"] == 5
        )
    return {
        "stores": 10,
        "node_ok": node_ok,
        "edge_ok": edge_ok,
        "dedup_ok": dedup_ok,
        "fields_ok": fields_ok,
        "count_ok": count_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "kg_export_eval.json"),
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
