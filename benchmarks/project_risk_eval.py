"""Project-risk eval (round 180, memory-driven risk management).

10 stores. Each store: 2 risk memories, a conflict pair, 2 plain memories,
1 overdue intent and 2 clashing intents. project_risk must score 70 (high)
with correct factors.
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


def _store(seed: int) -> tuple[MemoryEngine, MCPServer, list[str]]:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    ids = []
    for text, cue in (
        (f"风险：模型延迟高{seed}", "pr-1"),
        (f"注意：数据权限未确认{seed}", "pr-2"),
        (f"需求：支持中文多轮对话{seed}", "pr-3"),
        (f"记录了会议纪要{seed}", "pr-4"),
        (f"aaa conflict one {seed}", "conflict-key"),
        (f"bbb conflict two {seed}", "conflict-key"),
    ):
        item = engine.remember(
            text,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[cue],
            confidence=0.8 if cue == "conflict-key" else 1.0,
            auto_cues=False,
        )
        ids.append(item.id)
    engine.remember_intent(
        f"overdue {seed}", due_at=now - timedelta(hours=1)
    )
    engine.remember_intent(
        f"clash a {seed}", due_at=now + timedelta(minutes=10)
    )
    engine.remember_intent(
        f"clash b {seed}", due_at=now + timedelta(minutes=20)
    )
    return engine, MCPServer(engine=engine), ids


def _run() -> dict:
    score_ok = verdict_ok = factors_ok = previews_ok = empty_ok = fields_ok = (
        mcp_ok
    ) = 0
    for seed in range(10):
        engine, server, ids = _store(seed)
        report = engine.project_risk(memory_ids=ids)
        score_ok += int(report["risk_score"] == 70)
        verdict_ok += int(report["verdict"] == "high")
        factors_ok += int(
            report["factors"]
            == {
                "risk_memories": 2,
                "conflicts": 1,
                "overdue_intents": 1,
                "intent_clashes": 2,
            }
        )
        previews_ok += int(len(report["risk_memory_previews"]) >= 2)
        empty_ok += int(
            MemoryEngine().project_risk()["risk_score"] == 0
            and MemoryEngine().project_risk()["verdict"] == "low"
        )
        fields_ok += int(
            {"risk_score", "verdict", "factors",
             "risk_memory_previews", "suggestions"} <= set(report)
            and bool(report["suggestions"])
        )
        via_mcp = server._call_tool(
            "project_risk", {"memory_ids": ids}
        )
        mcp_ok += int(
            via_mcp["verdict"] == "high"
            and via_mcp["risk_score"] == 70
        )
    return {
        "stores": 10,
        "score_ok": score_ok,
        "verdict_ok": verdict_ok,
        "factors_ok": factors_ok,
        "previews_ok": previews_ok,
        "empty_ok": empty_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "project_risk_eval.json"),
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
