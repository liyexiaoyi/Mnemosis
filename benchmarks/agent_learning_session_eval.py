"""Agent-learning-session eval (round 252, end-to-end study loop).

10 stores. Each store: 3 mastered 偏好 memories. The session scores 2
attempts (1 correct, 1 wrong), diffs a second snapshot and plans the
next loop.
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


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    items = []
    for content in (
        "阿丽喜欢的城市是成都。",
        "阿丽喜欢的食物是饺子。",
        "阿丽喜欢的颜色是蓝色。",
    ):
        item = engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["偏好"],
            confidence=0.95,
            strength=0.9,
            importance=0.8,
            created_at=now - timedelta(days=30),
            auto_cues=False,
        )
        items.append(item)
    return engine, MCPServer(engine=engine), items


def _run() -> dict:
    fields_ok = baseline_ok = practice_ok = scoring_ok = diff_ok = (
        next_loop_ok
    ) = empty_ok = mcp_ok = 0
    for seed in range(10):
        engine, server, items = _store(seed)
        session = engine.agent_learning_session(
            [
                {"id": items[0].id, "attempt": "阿丽喜欢的城市是成都。"},
                {"id": items[1].id, "attempt": "完全错误"},
            ]
        )
        fields_ok += int(
            {
                "baseline",
                "practice",
                "scored",
                "session_result",
                "snapshot_after",
                "review_after",
                "next_loop",
                "verdict",
                "advice",
            }
            <= set(session)
        )
        baseline_ok += int(
            "total_memories" in session["baseline"]
            and "avg_retrievability" in session["baseline"]
        )
        practice_ok += int(
            session["practice"] is not None
            and len(session["practice"]["questions"]) > 0
        )
        scoring_ok += int(
            session["session_result"]["attempted"] == 2
            and session["session_result"]["correct"] == 1
            and abs(session["session_result"]["success_rate"] - 0.5) < 0.001
        )
        diff_ok += int(
            session["snapshot_after"]["diff"] is not None
            and session["snapshot_after"]["diff"]["verdict"]
            in ("improving", "stable", "declining")
        )
        next_loop_ok += int(
            [s["step"] for s in session["next_loop"]["steps"]]
            == ["清积压", "做练习", "拍快照"]
            and session["next_loop"]["focus_topic"] == "偏好"
        )
        empty = MemoryEngine().agent_learning_session()
        empty_ok += int(
            empty["verdict"] == "empty"
            and empty["session_result"]["attempted"] == 0
        )
        via_mcp = server._call_tool(
            "agent_learning_session",
            {
                "answers": [
                    {"id": items[0].id, "attempt": "阿丽喜欢的城市是成都。"}
                ]
            },
        )
        mcp_ok += int(
            via_mcp["session_result"]["correct"] == 1
            and via_mcp["snapshot_after"]["diff"] is not None
            and len(via_mcp["next_loop"]["steps"]) == 3
        )
    return {
        "stores": 10,
        "fields_ok": fields_ok,
        "baseline_ok": baseline_ok,
        "practice_ok": practice_ok,
        "scoring_ok": scoring_ok,
        "diff_ok": diff_ok,
        "next_loop_ok": next_loop_ok,
        "empty_ok": empty_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(
            _BENCH, "results", "agent_learning_session_eval.json"
        ),
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
