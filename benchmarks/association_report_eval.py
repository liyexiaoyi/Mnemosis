"""Association-report eval (round 125, Collins & Loftus 1975).

10 stores. Each store: 12 manual memories (6 hubs/nodes linked by hand,
6 isolated) + 2 automatic memories sharing a cue. association_report must
count directed/unique links, connected vs isolated memories, average
degree, and name the most-connected memory.
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
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    hub = engine.remember(
        "zzz hub one.", kind=MemoryKind.SEMANTIC, source=user
    )
    nodes = [
        engine.remember(
            f"qqq nod {i}.", kind=MemoryKind.SEMANTIC, source=user
        )
        for i in range(5)
    ]
    for i in range(6):
        engine.remember(
            f"aaa lon {i}.", kind=MemoryKind.SEMANTIC, source=user
        )
    for node in nodes:
        engine.backend.add_link(hub.id, node.id)
    engine.backend.add_link(nodes[0].id, nodes[1].id)
    engine.backend.add_link(nodes[2].id, nodes[3].id)
    engine.remember(
        "bbb auto one.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"samecue{seed}"],
    )
    engine.remember(
        "ccc auto two.",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"samecue{seed}"],
    )
    return engine


def _run() -> dict:
    count_ok = isolated_ok = connected_ok = top_ok = auto_ok = fields_ok = 0
    for seed in range(10):
        engine = _store(seed)
        report = engine.association_report(limit=5)
        count_ok += int(report["memory_count"] == 14)
        isolated_ok += int(report["isolated_count"] == 6)
        connected_ok += int(report["connected_count"] == 8)
        top = report["top_connected"]
        top_ok += int(
            len(top) >= 1
            and top[0]["link_count"] == 5
            and top[0]["kind"] == "semantic"
        )
        auto_ok += int(
            report["directed_links"] == 9
            and report["unique_pairs"] == 8
            and report["avg_links"] == round(18 / 14, 3)
        )
        fields_ok += int(
            {
                "memory_count",
                "directed_links",
                "unique_pairs",
                "connected_count",
                "isolated_count",
                "avg_links",
                "top_connected",
            }
            <= set(report)
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "isolated_ok": isolated_ok,
        "connected_ok": connected_ok,
        "top_ok": top_ok,
        "auto_ok": auto_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "association_report_eval.json"),
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
