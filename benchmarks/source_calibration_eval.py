"""Source-calibration eval (round 169, Johnson et al. 1993).

10 stores. Each store: 2 user memories (high confidence/evidence), 2
agent memories (low) and 2 document memories (medium). source_calibration
must rank user first with a higher trust score.
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

    def _remember(text: str, origin: SourceType, trust: float,
                  confidence: float, evidence: int,
                  importance: float) -> None:
        engine.remember(
            f"{text} {seed}",
            kind=MemoryKind.SEMANTIC,
            source=SourceRecord(origin=origin, trust=trust),
            cues=[f"sc-{text}{seed}"],
            confidence=confidence,
            evidence_count=evidence,
            importance=importance,
            auto_cues=False,
        )

    _remember("user fact 1", SourceType.USER, 1.0, 1.0, 5, 0.8)
    _remember("user fact 2", SourceType.USER, 1.0, 1.0, 5, 0.8)
    _remember("agent fact 1", SourceType.AGENT, 0.5, 0.6, 1, 0.4)
    _remember("agent fact 2", SourceType.AGENT, 0.5, 0.6, 1, 0.4)
    _remember("doc fact 1", SourceType.DOCUMENT, 0.9, 0.9, 3, 0.7)
    _remember("doc fact 2", SourceType.DOCUMENT, 0.9, 0.9, 3, 0.7)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    total_ok = origin_ok = order_ok = score_ok = fields_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.source_calibration()
        total_ok += int(report["total_memories"] == 6)
        by_origin = {s["origin"]: s for s in report["sources"]}
        origin_ok += int(
            set(by_origin) == {"user", "agent", "document"}
        )
        order_ok += int(report["sources"][0]["origin"] == "user")
        score_ok += int(
            by_origin["user"]["trust_score"]
            > by_origin["agent"]["trust_score"]
            and by_origin["user"]["avg_evidence"] == 5.0
        )
        fields_ok += int(
            {"sources", "total_memories"} <= set(report)
            and all(
                {"origin", "memory_count", "avg_confidence", "avg_evidence",
                 "avg_importance", "avg_source_trust", "trust_score"}
                <= set(s)
                for s in report["sources"]
            )
        )
        via_mcp = server._call_tool("source_calibration", {})
        mcp_ok += int(
            via_mcp["total_memories"] == 6
            and via_mcp["sources"][0]["origin"] == "user"
        )
    return {
        "stores": 10,
        "total_ok": total_ok,
        "origin_ok": origin_ok,
        "order_ok": order_ok,
        "score_ok": score_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "source_calibration_eval.json"),
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
