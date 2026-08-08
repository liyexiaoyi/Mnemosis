"""Learning-loop eval (round 251, review -> practice -> snapshot).

10 stores. Each store: 3 mastered 偏好 memories (one stale review) plus
one developing 物理 memory. learning_loop must return a baseline
snapshot, review counts, a focus topic, a practice question, the 3-step
loop and a legal verdict.
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
    for content in (
        "阿丽喜欢的城市是成都。",
        "阿丽喜欢的食物是饺子。",
        "阿丽喜欢的颜色是蓝色。",
    ):
        engine.remember(
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
    engine.remember(
        "物理公式：F=ma",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        confidence=0.6,
        strength=0.6,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    fields_ok = baseline_ok = review_ok = focus_ok = practice_ok = (
        steps_ok
    ) = empty_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        loop = engine.learning_loop()
        fields_ok += int(
            {
                "baseline",
                "review",
                "focus_topic",
                "practice",
                "steps",
                "verdict",
                "advice",
            }
            <= set(loop)
        )
        baseline_ok += int(
            "total_memories" in loop["baseline"]
            and "avg_retrievability" in loop["baseline"]
        )
        review_ok += int(
            "overdue_count" in loop["review"]
            and "never_reviewed_count" in loop["review"]
            and "adherence_ratio" in loop["review"]
        )
        focus_ok += int(loop["focus_topic"] == "物理")
        practice_ok += int(
            loop["practice"] is not None
            and len(loop["practice"]["questions"]) > 0
        )
        steps_ok += int(
            [s["step"] for s in loop["steps"]]
            == ["清积压", "做练习", "拍快照"]
        )
        empty = MemoryEngine().learning_loop()
        empty_ok += int(
            empty["verdict"] == "empty"
            and empty["focus_topic"] is None
            and "闭环" in empty["advice"]
        )
        via_mcp = server._call_tool("learning_loop", {"count": 1})
        mcp_ok += int(
            via_mcp["verdict"] == "ready"
            and len(via_mcp["steps"]) == 3
            and len(via_mcp["practice"]["questions"]) > 0
        )
    return {
        "stores": 10,
        "fields_ok": fields_ok,
        "baseline_ok": baseline_ok,
        "review_ok": review_ok,
        "focus_ok": focus_ok,
        "practice_ok": practice_ok,
        "steps_ok": steps_ok,
        "empty_ok": empty_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "learning_loop_eval.json"),
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
