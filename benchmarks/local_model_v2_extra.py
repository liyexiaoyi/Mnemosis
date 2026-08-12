"""Local model answers for the round 42-46 capability dimensions.

Runs qwen2.5:3b on: replan (does the written plan avoid 阿丽's failed
flight?) and prediction (which step had an unexpected failure?).
"""

from __future__ import annotations

import json
import os
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from compare_with_models import ollama_generate
from replan_bench import ALI_FLIGHT, GOAL
from replan_bench import build_engine as build_replan_engine

from mnemosis import MemoryEngine

MODEL = "qwen2.5:3b"
URL = "http://127.0.0.1:11434"


def main() -> int:
    report = {}

    # 1) replan: write a plan from the re-planned context
    engine = build_replan_engine()
    replanned = engine.replan(GOAL, "订机票")
    plan_ctx = [r.item.content for r in replanned]
    answer = ollama_generate(
        MODEL,
        "下面是重新规划后的参考计划。请为大壮写出调整后的旅行步骤计划，"
        "每步一行，避免失败过的步骤。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in plan_ctx)
        + f"\n\n目标：{GOAL}",
        URL,
        timeout=60,
    )
    report["replan"] = {
        "avoids_ali_flight": int(ALI_FLIGHT not in answer),
        "answer": answer,
    }
    print("replan avoids ali flight:", report["replan"]["avoids_ali_flight"],
          flush=True)

    # 2) prediction: locate the unexpected failure
    pe = MemoryEngine()
    for _ in range(5):
        pe.record_outcome("旅行", "订机票", success=True)
    pe.record_outcome("旅行", "订机票", success=False, note="航班取消")
    pe.record_outcome("搬家", "打包箱子", success=True)
    ctx = [r.item.content for r in pe.recall("意外 失败 订机票", top_k=5)]
    answer2 = ollama_generate(
        MODEL,
        "只用下面的记忆上下文回答；没有就答unknown。\n\n"
        "上下文：\n" + "\n".join(f"- {c}" for c in ctx)
        + "\n\n问题：哪个步骤出现过意外失败？",
        URL,
        timeout=60,
    )
    report["prediction"] = {
        "identifies_flight": int("机票" in answer2),
        "answer": answer2,
    }
    print("prediction identifies flight:",
          report["prediction"]["identifies_flight"], flush=True)

    out = os.path.join(_BENCH, "results", "local_model_v2_extra.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
