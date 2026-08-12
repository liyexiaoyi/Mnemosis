"""Practice-session eval (round 109).

30 due memories; one practice_session(limit=10, 30 answers). The plan
should hold 10 cards, the report should cover all 30 with difficulty
stats and per-card next-review suggestions.
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
from mnemosis.types import MemoryKind, SourceRecord, SourceType, utcnow


def _run() -> dict:
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    now = utcnow()
    items = []
    for i in range(30):
        item = engine.remember(
            f"会话条目{i}：内容。",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=[f"会话条目{i}"],
            importance=0.8,
            strength=0.3,
            created_at=now - timedelta(days=20),
        )
        items.append(item)
    answers = [
        {"id": item.id, "attempt": "测试"}
        for item in items
    ]
    session = engine.practice_session(answers, limit=10, now=now)
    plan_len = len(session["plan"])
    report = session["report"]
    suggestions = all(
        "next_review_at" in d for d in report["details"]
    )
    return {
        "plan_len": plan_len,
        "expected_plan": 10,
        "report_n": report["n"],
        "difficulty_n": report["difficulty"]["n"]
        if report["difficulty"] else None,
        "suggestions_ok": int(suggestions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "practice_session_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = bool(
        report["plan_len"] == report["expected_plan"]
        and report["report_n"] == 30
        and report["difficulty_n"] == 30
        and report["suggestions_ok"] == 1
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
