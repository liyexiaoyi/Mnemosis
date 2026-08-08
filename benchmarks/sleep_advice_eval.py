"""Sleep-advice eval (round 196, Rasch & Born 2013).

10 stores. Each store: a weak-important memory, a conflict pair, an
overdue intent and an unreviewed topic. sleep_advice must collect all
four signals.
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
    engine.remember(
        f"sleep weak important {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["sw-1"],
        importance=0.8,
        created_at=now - timedelta(days=30),
        auto_cues=False,
    )
    engine.remember(
        f"zzz conflict one {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["sleep-conflict"], confidence=0.8, auto_cues=False,
    )
    engine.remember(
        f"zzz conflict two {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["sleep-conflict"], confidence=0.8, auto_cues=False,
    )
    for i in range(2):
        engine.remember(
            f"blind topic {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["盲区主题"],
            auto_cues=False,
        )
    engine.remember_intent(
        f"sleep overdue {seed}", due_at=now - timedelta(hours=1)
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    review_ok = conflict_ok = overdue_ok = priority_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.sleep_advice(now=utcnow())
        review_ok += int(len(report["pre_sleep_review"]) >= 1)
        conflict_ok += int(report["conflicts_to_resolve"] >= 1)
        overdue_ok += int(report["overdue_intents"] >= 1)
        priority_ok += int(
            report["tomorrow_priorities"]
            and any(
                topic["topic"] == "盲区主题"
                for topic in report["tomorrow_priorities"]
            )
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"pre_sleep_review", "conflicts_to_resolve", "overdue_intents",
             "tomorrow_priorities", "advice"} <= set(report)
            and all(
                {"id", "preview", "importance", "retrievability"}
                <= set(item)
                for item in report["pre_sleep_review"]
            )
        )
        via_mcp = server._call_tool("sleep_advice", {})
        mcp_ok += int(
            len(via_mcp["pre_sleep_review"]) >= 1
            and via_mcp["conflicts_to_resolve"] >= 1
        )
    return {
        "stores": 10,
        "review_ok": review_ok,
        "conflict_ok": conflict_ok,
        "overdue_ok": overdue_ok,
        "priority_ok": priority_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "sleep_advice_eval.json"),
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
