"""Memory-health eval (round 144, Koriat & Goldsmith 1996).

10 stores. Each store has a hand-linked network, 2 isolated memories, a
conflict pair, a crowded cue cluster and 3 intentions (1 overdue + 2
clashing). memory_health must aggregate these into a 0-100 score with
consistent penalties and fields.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    hub = engine.remember(
        "zzz hub alpha.", kind=MemoryKind.SEMANTIC, source=user
    )
    nodes = [
        engine.remember(
            f"qqq nod {letter}.", kind=MemoryKind.SEMANTIC, source=user
        )
        for letter in ("x", "y", "z", "u", "v")
    ]
    for node in nodes:
        engine.backend.add_link(hub.id, node.id)
    for letter in ("m", "n"):
        engine.remember(
            f"aaa lon {letter}.", kind=MemoryKind.SEMANTIC, source=user
        )
    engine.remember(
        f"conflict alpha {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["conflict-key"], confidence=0.8, auto_cues=False,
    )
    engine.remember(
        f"conflict beta {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["conflict-key"], confidence=0.8, auto_cues=False,
    )
    for i in range(3):
        engine.remember(
            f"crowd {seed}-{i} item", kind=MemoryKind.SEMANTIC, source=user,
            cues=["会议"], auto_cues=False,
        )
    engine.remember_intent(
        f"overdue {seed}", due_at=now - timedelta(hours=1)
    )
    engine.remember_intent(
        f"clash a {seed}", due_at=now + timedelta(minutes=10)
    )
    engine.remember_intent(
        f"clash b {seed}", due_at=now + timedelta(minutes=20)
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    score_ok = linked_ok = counts_ok = penalty_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        health = engine.memory_health()
        score_ok += int(0 <= health["score"] < 100)
        linked_ok += int(health["linked_ratio"] == round(11 / 13, 3))
        counts_ok += int(
            health["crowded_clusters"] >= 1
            and health["conflicts"] >= 1
            and health["overdue_intents"] >= 1
            and health["intent_clashes"] >= 1
        )
        penalty_ok += int(
            sum(health["penalties"].values()) > 0
            and health["score"]
            == max(0, 100 - sum(health["penalties"].values()))
        )
        fields_ok += int(
            {"score", "memory_count", "linked_ratio", "crowded_clusters",
             "conflicts", "overdue_intents", "intent_clashes",
             "suppressed_count", "penalties"} <= set(health)
            and health["memory_count"] == 13
        )
        via_mcp = server._call_tool("memory_health", {})
        mcp_ok += int(
            via_mcp["memory_count"] == 13
            and "penalties" in via_mcp
            and 0 <= via_mcp["score"] <= 100
        )
    return {
        "stores": 10,
        "score_ok": score_ok,
        "linked_ok": linked_ok,
        "counts_ok": counts_ok,
        "penalty_ok": penalty_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "memory_health_eval.json"),
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
