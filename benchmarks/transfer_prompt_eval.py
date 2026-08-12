"""Transfer-prompt eval (round 235, far transfer).

10 stores. Each store: a mastered math topic (2 items, 90% accuracy) and
a new physics memory. transfer_prompt must pick the mastered topic and
generate hidden-answer application questions.
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
    for i in range(2):
        item = engine.remember(
            f"数学公式 {seed}-{i}",
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["数学"],
            confidence=0.9,
            strength=0.9,
            auto_cues=False,
        )
        item.retrieval_successes = 9
        item.retrieval_failures = 1
        engine.backend.update(item)
    engine.remember(
        f"物理新概念 {seed}",
        kind=MemoryKind.SEMANTIC,
        source=user,
        cues=["物理"],
        confidence=0.4,
        strength=0.4,
        auto_cues=False,
    )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    topic_ok = prompt_ok = hidden_ok = id_ok = transfer_ok = advice_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.transfer_prompt(count=2)
        topic_ok += int(report["topics"][0]["topic"] == "数学")
        prompt_ok += int(len(report["prompts"]) >= 1)
        hidden_ok += int(
            all(
                prompt["answer_hidden"]
                for prompt in report["prompts"]
            )
        )
        id_ok += int(
            all(
                engine.backend.get(prompt["memory_id"]) is not None
                for prompt in report["prompts"]
            )
        )
        transfer_ok += int("迁移" in report["prompts"][0]["question"])
        advice_ok += int(bool(report["advice"]))
        fields_ok += int(
            {"topics", "prompts", "advice"} <= set(report)
            and all(
                {"topic", "mastery"} <= set(topic)
                for topic in report["topics"]
            )
            and all(
                {"memory_id", "topic", "question", "hint_cues",
                 "answer_hidden"}
                <= set(prompt)
                for prompt in report["prompts"]
            )
        )
        via_mcp = server._call_tool("transfer_prompt", {"count": 2})
        mcp_ok += int(
            via_mcp["topics"][0]["topic"] == "数学"
            and len(via_mcp["prompts"]) >= 1
        )
    return {
        "stores": 10,
        "topic_ok": topic_ok,
        "prompt_ok": prompt_ok,
        "hidden_ok": hidden_ok,
        "id_ok": id_ok,
        "transfer_ok": transfer_ok,
        "advice_ok": advice_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "transfer_prompt_eval.json"),
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
