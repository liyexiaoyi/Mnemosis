"""Nightly-routine eval (round 230, sleep + testing pipeline).

10 stores. Each store: two decayed physics memories (sleep inference
pair) plus two strong memories. nightly_routine must compose tonight's
review, sleep pairs and tomorrow's quiz.
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
    for content in (f"引力使苹果落地 {seed}", f"质量越大引力越大 {seed}"):
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            importance=0.7,
            strength=0.5,
            created_at=now - timedelta(days=20),
            auto_cues=False,
        )
    for i in range(2):
        engine.remember(
            f"熟记要点 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["要点"],
            importance=0.8,
            strength=0.95,
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    tonight_ok = sleep_ok = quiz_ok = ids_ok = count_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.nightly_routine(review_limit=3, quiz_count=3)
        tonight_ok += int(len(report["tonight_review"]) >= 1)
        sleep_ok += int(report["sleep_inference_pairs"] >= 1)
        quiz_ok += int(
            len(report["tomorrow_quiz"]) == 3
            and all(
                question["answer_hidden"]
                for question in report["tomorrow_quiz"]
            )
        )
        ids_ok += int(
            all(
                engine.backend.get(question["memory_id"]) is not None
                for question in report["tomorrow_quiz"]
            )
        )
        count_ok += int(len(report["tonight_review"]) <= 3)
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {
                "tonight_review",
                "sleep_inference_pairs",
                "tomorrow_quiz",
                "advice",
            }
            <= set(report)
            and all(
                {"id", "preview", "score"} <= set(item)
                for item in report["tonight_review"]
            )
            and all(
                {"memory_id", "question", "qtype", "hint_cues",
                 "answer_hidden"}
                <= set(question)
                for question in report["tomorrow_quiz"]
            )
        )
        via_mcp = server._call_tool(
            "nightly_routine", {"review_limit": 3, "quiz_count": 3}
        )
        mcp_ok += int(
            len(via_mcp["tomorrow_quiz"]) == 3
            and via_mcp["sleep_inference_pairs"] >= 1
            and len(via_mcp["tonight_review"]) >= 1
        )
    return {
        "stores": 10,
        "tonight_ok": tonight_ok,
        "sleep_ok": sleep_ok,
        "quiz_ok": quiz_ok,
        "ids_ok": ids_ok,
        "count_ok": count_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "nightly_routine_eval.json"),
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
