"""Recognition-check eval (round 136, Yonelinas 2002).

10 stores. Each store: 3 memories. A full-cue query must classify as
recollection, a partial query as familiarity, an unrelated query as
unmatched and a missing id as missing.
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


def _store(seed: int) -> MemoryEngine:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    m1 = engine.remember(
        f"alpha unique zebra {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["alpha-key"],
        auto_cues=False,
    )
    m2 = engine.remember(
        f"beta term {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["beta-key"],
        auto_cues=False,
    )
    m3 = engine.remember(
        f"gamma unrelated {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["gamma-key"],
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine), m1.id, m3.id


def _run() -> dict:
    rec_ok = fam_ok = miss_ok = missing_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, m1id, m3id = _store(seed)
        rec = engine.recognition_check("alpha-key", m1id)
        rec_ok += int(rec["verdict"] == "recollection")
        fam = engine.recognition_check("alpha extra", m1id)
        fam_ok += int(fam["verdict"] == "familiarity")
        miss = engine.recognition_check("alpha-key", m3id)
        miss_ok += int(miss["verdict"] == "unmatched")
        missing = engine.recognition_check("alpha-key", "missing-id")
        missing_ok += int(missing["verdict"] == "missing")
        fields_ok += int(
            {"memory_id", "verdict", "score", "overlap", "confidence",
             "reasons"} <= set(rec)
            and isinstance(rec["reasons"], list)
        )
        via_mcp = server._call_tool(
            "recognition_check", {"query": "alpha-key", "memory_id": m1id}
        )
        mcp_ok += int(via_mcp["verdict"] == "recollection")
    return {
        "stores": 10,
        "rec_ok": rec_ok,
        "fam_ok": fam_ok,
        "miss_ok": miss_ok,
        "missing_ok": missing_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "recognition_check_eval.json"),
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
