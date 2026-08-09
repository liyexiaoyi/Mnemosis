"""Prediction-error driven memory update benchmark (round 46).

订机票 has 5 successes then an unexpected failure; 买相机 has 5 successes
then an expected success. Surprising outcomes should get higher importance
and an 意外 cue, be retrievable, and the step prediction should update.
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


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "prediction_error_bench.json"),
    )
    args = parser.parse_args()
    engine = MemoryEngine()
    for _ in range(5):
        engine.record_outcome("旅行", "订机票", success=True)
    before = engine.predict_step("订机票")
    surprising = engine.record_outcome(
        "旅行", "订机票", success=False, note="航班取消"
    )
    after = engine.predict_step("订机票")
    for _ in range(5):
        engine.record_outcome("搬家", "打包箱子", success=True)
    expected = engine.record_outcome("搬家", "打包箱子", success=True)

    report = {
        "predict_before": before,
        "predict_after": after,
        "surprising_importance": surprising.importance,
        "surprising_has_alert_cue": int("\u610f\u5916" in surprising.cues),
        "expected_importance": expected.importance,
        "expected_no_alert_cue": int("\u610f\u5916" not in expected.cues),
        "surprising_retrievable": int(
            any(
                "\u610f\u5916" in r.item.content or "航班取消" in r.item.content
                for r in engine.recall("意外 失败", top_k=5)
            )
        ),
    }
    report["all_ok"] = bool(
        before["success_probability"] == 1.0
        and abs(after["success_probability"] - 5 / 6) < 0.01
        and surprising.importance >= 0.85
        and report["surprising_has_alert_cue"]
        and expected.importance < surprising.importance
        and report["expected_no_alert_cue"]
        and report["surprising_retrievable"]
    )
    print("predict before:", before, flush=True)
    print("predict after:", after, flush=True)
    print("surprising importance:", surprising.importance,
          "alert cue:", report["surprising_has_alert_cue"], flush=True)
    print("expected importance:", expected.importance,
          "no alert:", report["expected_no_alert_cue"], flush=True)
    print("all_ok:", report["all_ok"], flush=True)

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        ctx = [
            r.item.content
            for r in engine.recall("意外 失败 订机票", top_k=5)
        ]
        answer = cloud_generate(
            "只用下面的记忆上下文回答；没有就答unknown。\n\n"
            "上下文：\n" + "\n".join(f"- {c}" for c in ctx)
            + "\n\n问题：哪个步骤出现过意外失败？"
        )
        report["llm"] = {
            "answer": answer,
            "identifies_flight": int("机票" in answer),
        }
        print("llm identifies flight:", report["llm"]["identifies_flight"],
              flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
