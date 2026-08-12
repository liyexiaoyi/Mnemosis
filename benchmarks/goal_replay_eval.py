"""Goal-replay eval (round 205, replay-based planning).

10 stores. Each store: two past moving episodes (one success, one
failure) plus an overdue intention. goal_replay must recall evidence,
extract lessons, reactivate the overdue intent and score readiness.
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

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    engine.remember(
        f"上次搬家 打包箱子 成功 {seed}",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["搬家"],
        auto_cues=False,
    )
    engine.remember(
        f"上次搬家 找搬家公司 失败 {seed}",
        kind=MemoryKind.EPISODIC,
        source=user,
        cues=["搬家"],
        auto_cues=False,
    )
    engine.remember_intent(
        f"预约搬家公司 {seed}",
        due_at=utcnow() - timedelta(hours=1),
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    evidence_ok = lesson_ok = react_ok = step_ok = score_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.goal_replay("搬家")
        evidence_ok += int(len(report["evidence_used"]) >= 1)
        lesson_ok += int(report["lessons_found"] >= 1)
        react_ok += int(report["overdue_reactivations"] >= 1)
        step_ok += int(
            [step["order"] for step in report["replay_steps"]] == [1, 2, 3, 4]
            and all(
                step["verdict"] in ("ok", "weak")
                for step in report["replay_steps"]
            )
        )
        score_ok += int(0 <= report["replay_score"] <= 1)
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {
                "goal",
                "evidence_used",
                "lessons_found",
                "overdue_reactivations",
                "replay_steps",
                "replay_score",
                "advice",
            }
            <= set(report)
            and all(
                {"id", "preview", "kind", "score", "has_lesson"}
                <= set(item)
                for item in report["evidence_used"]
            )
        )
        via_mcp = server._call_tool("goal_replay", {"goal": "搬家"})
        mcp_ok += int(
            via_mcp["lessons_found"] >= 1
            and via_mcp["overdue_reactivations"] >= 1
            and 0 <= via_mcp["replay_score"] <= 1
        )
    return {
        "stores": 10,
        "evidence_ok": evidence_ok,
        "lesson_ok": lesson_ok,
        "react_ok": react_ok,
        "step_ok": step_ok,
        "score_ok": score_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "goal_replay_eval.json"),
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
