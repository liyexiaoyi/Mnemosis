"""Analogy-prompt eval (round 247, analogical encoding).

10 stores. Each store: 3 mastered 偏好 memories. analogy_prompt must
produce a same-structure / new-surface question (换皮不变骨) and stay
graceful on an empty store.
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
    contents = (
        "阿丽喜欢的城市是成都。",
        "阿丽喜欢的食物是饺子。",
        "阿丽喜欢的颜色是蓝色。",
    )
    for content in contents:
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=["偏好"],
            confidence=0.95,
            strength=0.9,
            importance=0.8,
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    prompts_ok = structure_ok = surface_ok = mapping_ok = hidden_ok = (
        topic_ok
    ) = empty_ok = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.analogy_prompt(count=3)
        prompts_ok += int(len(report["prompts"]) > 0)
        first = report["prompts"][0]
        structure_ok += int("喜欢" in first["question"])
        surface_ok += int(first["question"] != first["original"])
        mapping_ok += int(bool(first["surface_mapping"]))
        hidden_ok += int(first["answer_hidden"] is True)
        topic_ok += int(first["topic"] == "偏好")
        empty = MemoryEngine().analogy_prompt()
        empty_ok += int(
            empty["prompts"] == [] and "记忆库" in empty["advice"]
        )
        via_mcp = server._call_tool("analogy_prompt", {"count": 2})
        mcp_ok += int(
            len(via_mcp["prompts"]) > 0
            and via_mcp["prompts"][0]["question"]
            != via_mcp["prompts"][0]["original"]
        )
    return {
        "stores": 10,
        "prompts_ok": prompts_ok,
        "structure_ok": structure_ok,
        "surface_ok": surface_ok,
        "mapping_ok": mapping_ok,
        "hidden_ok": hidden_ok,
        "topic_ok": topic_ok,
        "empty_ok": empty_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "analogy_prompt_eval.json"),
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
