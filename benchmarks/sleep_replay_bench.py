"""Sleep replay / consolidation benchmark (round 49).

订机票 5 successes + 1 unexpected failure; 买相机 3 successes; 打包箱子 2
successes + 1 ordinary failure. sleep_replay() should replay the surprising
record, consolidate each step's experience into a "历史成功率" summary, and
predict_step should then use the consolidated summary.
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


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    for _ in range(5):
        engine.record_outcome("旅行", "订机票", success=True)
    surprising = engine.record_outcome(
        "旅行", "订机票", success=False, note="航班取消"
    )
    for _ in range(3):
        engine.record_outcome("旅行", "买相机", success=True)
    for _ in range(2):
        engine.record_outcome("搬家", "打包箱子", success=True)
    engine.record_outcome("搬家", "打包箱子", success=False, note="箱子不够")
    return engine, surprising


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "sleep_replay_bench.json"),
    )
    args = parser.parse_args()
    engine, surprising = build_engine()
    retrieval_before = surprising.retrieval_successes
    before_summary = engine.recall("订机票 历史成功率", top_k=3)
    report = {"summary_before": int(
        any("历史成功率" in r.item.content for r in before_summary)
    )}
    replay = engine.sleep_replay()
    report["replayed_surprising"] = replay["replayed_surprising"]
    report["consolidated_steps"] = replay["consolidated_steps"]
    report["surprising_replayed"] = int(
        surprising.retrieval_successes > retrieval_before
    )
    pred = engine.predict_step("订机票")
    report["predict"] = pred
    report["predict_via_consolidated"] = int(pred.get("source") == "consolidated")
    summary = engine.recall("订机票 历史成功率", top_k=3)
    report["summary_after"] = int(
        any("历史成功率" in r.item.content for r in summary)
    )
    report["all_ok"] = bool(
        not report["summary_before"]
        and replay["replayed_surprising"] == 2
        and replay["consolidated_steps"] == 3
        and report["surprising_replayed"]
        and abs(pred["success_probability"] - 5 / 6) < 0.01
        and report["predict_via_consolidated"]
        and report["summary_after"]
    )
    print("replay:", replay, flush=True)
    print("predict:", pred, flush=True)
    print("all_ok:", report["all_ok"], flush=True)

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        ctx = [r.item.content for r in summary]
        answer = cloud_generate(
            "只用下面的记忆上下文回答；没有就答unknown。\n\n"
            "上下文：\n" + "\n".join(f"- {c}" for c in ctx)
            + "\n\n问题：订机票的历史成功率是多少？"
        )
        report["llm"] = {
            "answer": answer,
            "correct_ratio": int("5" in answer and "6" in answer),
        }
        print("llm correct ratio:", report["llm"]["correct_ratio"],
              flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
