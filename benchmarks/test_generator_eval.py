"""Test-generator eval (round 213, testing effect).

10 stores. Each store: 4 physics facts. test_generator must produce 4
hidden-answer questions (cue prompts + cloze) for self-testing.
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

from mnemosis import MemoryEngine
from mnemosis.mcp_server import MCPServer
from mnemosis.types import MemoryKind, SourceRecord, SourceType


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    contents = [
        f"牛顿第二定律 F 等于 ma {seed}",
        f"光速约每秒 30 万千米 {seed}",
        f"水的沸点是 100 摄氏度 {seed}",
        f"地球绕太阳一圈约 365 天 {seed}",
    ]
    for content in contents:
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["物理"],
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    count_ok = hide_ok = type_ok = id_ok = cue_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.test_generator(topic="物理", count=4)
        count_ok += int(report["question_count"] == 4)
        hide_ok += int(
            all(
                not any(
                    item.content in question["question"]
                    for item in engine.store.all_active()
                    if item.id == question["memory_id"]
                )
                and question["answer_hidden"]
                for question in report["questions"]
            )
        )
        qtypes = {question["qtype"] for question in report["questions"]}
        type_ok += int(qtypes == {"cue_prompt", "cloze"})
        id_ok += int(
            all(
                engine.backend.get(question["memory_id"]) is not None
                for question in report["questions"]
            )
        )
        cue_ok += int(
            all(
                question["hint_cues"]
                and question["hint_cues"][0] == "物理"
                for question in report["questions"]
            )
        )
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"topic", "question_count", "questions", "advice"} <= set(report)
            and all(
                {"memory_id", "question", "qtype", "hint_cues",
                 "answer_hidden"}
                <= set(question)
                for question in report["questions"]
            )
        )
        via_mcp = server._call_tool(
            "test_generator", {"topic": "物理", "count": 4}
        )
        mcp_ok += int(
            via_mcp["question_count"] == 4
            and all(
                question["answer_hidden"]
                for question in via_mcp["questions"]
            )
        )
    return {
        "stores": 10,
        "count_ok": count_ok,
        "hide_ok": hide_ok,
        "type_ok": type_ok,
        "id_ok": id_ok,
        "cue_ok": cue_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "test_generator_eval.json"),
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
