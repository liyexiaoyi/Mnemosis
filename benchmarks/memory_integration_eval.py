"""Memory-integration eval (round 201, compositional inference).

10 stores. Each store: 4 same-topic semantic memories (schema candidate),
2 nearby episodes (event chain), 2 conflicting facts, 1 isolated memory.
memory_integration must suggest schemas, chains and conflict resolution.
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
from mnemosis.types import (  # noqa: E402
    MemoryKind,
    SourceRecord,
    SourceType,
    utcnow,
)


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for i in range(4):
        engine.remember(
            f"physics fact {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.7,
            auto_cues=False,
        )
    now = utcnow()
    engine.remember(
        f"trip day one {seed}",
        kind=MemoryKind.EPISODIC,
        source=SourceRecord(
            origin=SourceType.USER,
            occurred_at=now - timedelta(days=2),
        ),
        cues=["旅行"],
        auto_cues=False,
    )
    engine.remember(
        f"trip day two {seed}",
        kind=MemoryKind.EPISODIC,
        source=SourceRecord(
            origin=SourceType.USER,
            occurred_at=now,
        ),
        cues=["旅行"],
        auto_cues=False,
    )
    engine.remember(
        f"meeting on monday {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["日期"],
        confidence=0.9,
        auto_cues=False,
    )
    engine.remember(
        f"meeting on tuesday {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["日期"],
        confidence=0.9,
        auto_cues=False,
    )
    engine.remember(
        f"isolated note {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=[f"独一{seed}"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = schema_ok = chain_ok = conflict_ok = advice_ok = (
        sort_ok
    ) = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.memory_integration(limit=10)
        total_ok += int(report["total_memories"] == 9)
        schema_ok += int(
            any(
                candidate["topic"] == "物理"
                and candidate["count"] == 4
                for candidate in report["schema_candidates"]
            )
        )
        chain_ok += int(
            any(
                chain["topic"] == "旅行"
                and chain["events"] == 2
                and chain["span_days"] == 2.0
                for chain in report["event_chains"]
            )
        )
        conflict_ok += int(report["conflicts"] >= 1)
        advice_ok += int("冲突" in report["advice"])
        sort_ok += int(
            all(
                report["schema_candidates"][i]["count"]
                >= report["schema_candidates"][i + 1]["count"]
                for i in range(len(report["schema_candidates"]) - 1)
            )
        )
        fields_ok += int(
            {
                "total_memories",
                "schema_candidates",
                "event_chains",
                "conflicts",
                "advice",
            }
            <= set(report)
            and all(
                {"topic", "count", "avg_importance", "linked_pairs",
                 "suggestion"}
                <= set(candidate)
                for candidate in report["schema_candidates"]
            )
            and all(
                {"topic", "events", "span_days", "suggestion"}
                <= set(chain)
                for chain in report["event_chains"]
            )
        )
        via_mcp = server._call_tool("memory_integration", {})
        mcp_ok += int(
            via_mcp["conflicts"] >= 1
            and any(
                candidate["topic"] == "物理" and candidate["count"] == 4
                for candidate in via_mcp["schema_candidates"]
            )
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "schema_ok": schema_ok,
        "chain_ok": chain_ok,
        "conflict_ok": conflict_ok,
        "advice_ok": advice_ok,
        "sort_ok": sort_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "memory_integration_eval.json"),
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
