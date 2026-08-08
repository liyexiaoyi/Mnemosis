"""Bridge-suggestions eval (round 171, Collins & Loftus 1975).

10 stores. Each store: two unlinked pairs sharing a cue and one already
linked pair. bridge_suggestions must suggest exactly the two unlinked
pairs.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, str, str, str, str, str]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    a = engine.remember(
        f"bridge alpha {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["共同"], auto_cues=False,
    )
    b = engine.remember(
        f"bridge beta {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=[f"temp-b{seed}"], auto_cues=False,
    )
    b.cues = ["共同"]
    engine.backend.update(b)
    c = engine.remember(
        f"bridge gamma {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["也共同"], auto_cues=False,
    )
    d = engine.remember(
        f"bridge delta {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=[f"temp-d{seed}"], auto_cues=False,
    )
    d.cues = ["也共同"]
    engine.backend.update(d)
    e = engine.remember(
        f"bridge epsilon {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=["已有"], auto_cues=False,
    )
    f = engine.remember(
        f"bridge zeta {seed}", kind=MemoryKind.SEMANTIC, source=user,
        cues=[f"temp-f{seed}"], auto_cues=False,
    )
    f.cues = ["已有"]
    engine.backend.update(f)
    engine.backend.add_link(e.id, f.id)
    engine.backend.add_link(f.id, e.id)
    return (
        engine, MCPServer(engine=engine),
        a.id, b.id, c.id, d.id, e.id, f.id,
    )


def _run() -> dict:
    found_ok = pairs_ok = skip_ok = cues_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, a, b, c, d, e, f = _store(seed)
        report = engine.bridge_suggestions(limit=10)
        found_ok += int(report["total"] == 2)
        pairs = {
            frozenset((s["id_a"], s["id_b"]))
            for s in report["suggestions"]
        }
        pairs_ok += int(
            frozenset((a, b)) in pairs
            and frozenset((c, d)) in pairs
        )
        skip_ok += int(frozenset((e, f)) not in pairs)
        ab = next(
            s for s in report["suggestions"]
            if {s["id_a"], s["id_b"]} == {a, b}
        )
        cues_ok += int(ab["shared_cues"] == ["共同"])
        fields_ok += int(
            {"total", "suggestions"} <= set(report)
            and all(
                {"id_a", "id_b", "a_preview", "b_preview", "shared_cues"}
                <= set(s)
                for s in report["suggestions"]
            )
        )
        via_mcp = server._call_tool("bridge_suggestions", {"limit": 10})
        mcp_ok += int(via_mcp["total"] == 2)
    return {
        "stores": 10,
        "found_ok": found_ok,
        "pairs_ok": pairs_ok,
        "skip_ok": skip_ok,
        "cues_ok": cues_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "bridge_suggestions_eval.json"),
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
