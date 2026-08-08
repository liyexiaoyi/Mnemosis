"""Concept-cover eval (round 255, agent-visible chunked retrieval).

10 stores. Each store: speed/jump memories plus speed-themed distractors.
concept_cover must split the multi-concept question, report per-chunk
coverage, surface both concepts in the final top-k and through the MCP
search / context_pack chain.
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


def _store(seed: int):
    engine = MemoryEngine()
    user = SourceRecord(origin=SourceType.USER)
    for content, cues in (
        ("玩家移动速度为 320 像素/秒。", ["速度"]),
        ("跳跃力度为 420。", ["跳跃"]),
        ("主场景是 Main.tscn。", ["场景"]),
        ("玩家移动速度测试记录：昨天调到 300。", ["速度"]),
        ("玩家移动速度对比：周日 280，周一 300。", ["速度"]),
        ("音效音量默认 -6 dB。", ["音效"]),
    ):
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=user,
            cues=cues,
            auto_cues=False,
        )
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    fields_ok = chunks_ok = per_chunk_ok = covered_ok = final_ok = (
        verdict_ok
    ) = advice_ok = mcp_ok = 0
    query = "玩家移动速度和跳跃力度分别是多少？"
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.concept_cover(query, top_k=2)
        fields_ok += int(
            {
                "query",
                "multi_concept",
                "chunks",
                "per_chunk",
                "final_top_k",
                "verdict",
                "advice",
            }
            <= set(report)
        )
        chunks_ok += int(
            report["multi_concept"] is True and len(report["chunks"]) == 2
        )
        per_chunk_ok += int(
            len(report["per_chunk"]) == 2
            and all(
                "terms" in entry
                and "covered" in entry
                and "candidates" in entry
                for entry in report["per_chunk"]
            )
        )
        covered_ok += int(
            all(entry["covered"] for entry in report["per_chunk"])
        )
        finals = [row["preview"] for row in report["final_top_k"]]
        final_ok += int(
            any("320" in row for row in finals)
            and any("420" in row for row in finals)
        )
        verdict_ok += int(report["verdict"] == "multi")
        advice_ok += int("覆盖" in report["advice"])
        via_mcp = server._call_tool(
            "concept_cover", {"query": query, "top_k": 2}
        )
        via_search = server._call_tool(
            "search", {"query": query, "top_k": 2}
        )
        via_pack = server._call_tool(
            "context_pack", {"queries": [query], "top_k": 2}
        )
        mcp_ok += int(
            via_mcp["multi_concept"] is True
            and all(entry["covered"] for entry in via_mcp["per_chunk"])
            and any("320" in r["content"] for r in via_search)
            and any("420" in r["content"] for r in via_search)
            and any("320" in r["content"] for r in via_pack["packed"])
            and any("420" in r["content"] for r in via_pack["packed"])
        )
    return {
        "stores": 10,
        "fields_ok": fields_ok,
        "chunks_ok": chunks_ok,
        "per_chunk_ok": per_chunk_ok,
        "covered_ok": covered_ok,
        "final_ok": final_ok,
        "verdict_ok": verdict_ok,
        "advice_ok": advice_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "concept_cover_eval.json"),
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
