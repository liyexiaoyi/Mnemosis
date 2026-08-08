"""Suppress-memories eval (round 134, Anderson & Green 2001).

10 stores. Each store: 3 memories (sup-a / sup-b / sup-c). Suppressing
sup-a must block it from recall while keeping the trace intact and the
other memories reachable; unsuppress restores it; export/import keeps the
suppressed state.
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
    a = engine.remember(
        f"aaa suppress {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["sup-a"],
        auto_cues=False,
    )
    b = engine.remember(
        f"bbb keep {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["sup-b"],
        auto_cues=False,
    )
    c = engine.remember(
        f"ccc keep {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["sup-c"],
        auto_cues=False,
    )
    return engine, a.id, b.id


def _run() -> dict:
    suppress_ok = intact_ok = keep_ok = report_ok = unsuppress_ok = (
        roundtrip_ok
    ) = fields_ok = 0
    for seed in range(10):
        engine, aid, bid = _store(seed)
        result = engine.suppress_memories([aid])
        suppress_ok += int(
            result["suppressed"] == 1
            and aid not in {r.item.id for r in engine.recall("sup-a", top_k=3)}
        )
        intact_ok += int(len(engine.store.all_active()) == 3)
        keep_ok += int(
            bid in {r.item.id for r in engine.recall("sup-b", top_k=3)}
        )
        report = engine.suppressed_report()
        report_ok += int(
            report["count"] == 1 and report["memories"][0]["id"] == aid
        )
        engine.unsuppress_memories([aid])
        unsuppress_ok += int(
            aid in {r.item.id for r in engine.recall("sup-a", top_k=3)}
        )
        engine.suppress_memories([bid])
        payload = engine.export_memories()
        fresh = MemoryEngine()
        fresh.import_memories(payload)
        roundtrip_ok += int(
            fresh.suppressed_report()["count"] == 1
            and bid not in {r.item.id for r in fresh.recall("sup-b", top_k=3)}
        )
        fields_ok += int(
            {"count", "memories"} <= set(report)
            and {"id", "preview", "suppressed_at"}
            <= set(report["memories"][0])
        )
    return {
        "stores": 10,
        "suppress_ok": suppress_ok,
        "intact_ok": intact_ok,
        "keep_ok": keep_ok,
        "report_ok": report_ok,
        "unsuppress_ok": unsuppress_ok,
        "roundtrip_ok": roundtrip_ok,
        "fields_ok": fields_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "suppress_memories_eval.json"),
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
