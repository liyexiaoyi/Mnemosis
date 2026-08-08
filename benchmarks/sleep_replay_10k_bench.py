"""Post-sleep-replay retrieval stability at 10k (round 50).

Reuses the unexpected-event 10k store (8,856 memories, 1 surprising 订机票
failure + 30 ordinary failures). After sleep_replay(): the surprising record
is replayed, its step gets a consolidated "历史成功率" summary, retrieval of
"哪个步骤出现过意外失败？" stays top-1, and predict_step uses the summary.
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

from unexpected_event_10k_bench import TARGET_RECORD, build_engine  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "sleep_replay_10k_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine(use_mechanism=True)
    before = engine.recall("哪个步骤出现过意外失败？", top_k=5)
    before_ctx = [r.item.content for r in before]
    replay = engine.sleep_replay()
    after = engine.recall("哪个步骤出现过意外失败？", top_k=5)
    after_ctx = [r.item.content for r in after]
    pred = engine.predict_step("订机票")
    summary = engine.recall("订机票 历史成功率", top_k=3)
    report = {
        "memories": len(engine.store.all_active()),
        "before_top1_target": int(
            bool(before_ctx) and before_ctx[0] == TARGET_RECORD
        ),
        "replayed_surprising": replay["replayed_surprising"],
        "consolidated_steps": replay["consolidated_steps"],
        "after_top1_target": int(
            bool(after_ctx) and after_ctx[0] == TARGET_RECORD
        ),
        "target_summary_retrievable": int(
            any("历史成功率" in r.item.content for r in summary)
        ),
        "predict_via_summary": int(pred.get("source") == "consolidated"),
        "predict_ratio": pred["success_probability"],
    }
    report["all_ok"] = bool(
        report["before_top1_target"]
        and replay["replayed_surprising"] == 1
        and report["consolidated_steps"] >= 1
        and report["after_top1_target"]
        and report["target_summary_retrievable"]
        and report["predict_via_summary"]
        and abs(report["predict_ratio"] - 5 / 6) < 0.01
    )
    print("memories:", report["memories"], flush=True)
    print("replay:", replay, flush=True)
    print("before/after top1:", report["before_top1_target"],
          report["after_top1_target"], flush=True)
    print("predict:", pred, flush=True)
    print("all_ok:", report["all_ok"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
