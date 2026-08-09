"""Re-planning benchmark (round 44, error monitoring -> re-plan).

阿丽's 订机票 failed twice; 小波's steps all succeeded. After reporting the
failed step, replan() should move ONLY 阿丽's flight step to the end (with a
重规划 reason), keep 小波's successful flight, and store the re-planning
decision. Compares replan vs the plain outcome-aware plan.
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
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


GOAL = "大壮想去京都旅行，参考阿丽和小波"
ALI_FLIGHT = "阿丽在2026年4月1日订了去京都的机票。"
XIAOBO_FLIGHT = "小波在2026年5月1日订了去京都的机票。"


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content, person, iso in (
        (ALI_FLIGHT, "阿丽", "2026-04-01"),
        ("阿丽在2026年4月2日买了相机。", "阿丽", "2026-04-02"),
        (XIAOBO_FLIGHT, "小波", "2026-05-01"),
        ("小波在2026年5月2日买了相机。", "小波", "2026-05-02"),
    ):
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, iso],
        )
    engine.record_outcome("阿丽旅行", "订机票", success=False, note="航班取消")
    engine.record_outcome("阿丽旅行", "订机票", success=False, note="再次取消")
    engine.record_outcome("小波旅行", "订机票", success=True)
    engine.record_outcome("小波旅行", "买相机", success=True)
    return engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--llm", action="store_true")
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "replan_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    replanned = engine.replan(GOAL, "订机票")
    replan_contents = [r.item.content for r in replanned]
    plan = engine.plan_for_goal(GOAL, effort="high")
    plan_contents = [r.item.content for r in plan]

    report = {
        "replan": {
            "ali_flight_at_end": int(
                replan_contents.index(ALI_FLIGHT)
                == len(replan_contents) - 1
            ),
            "xiaobo_flight_kept_early": int(
                replan_contents.index(XIAOBO_FLIGHT)
                < replan_contents.index(ALI_FLIGHT)
            ),
            "replan_reason": int(
                any(
                    "\u91cd\u89c4\u5212" in reason
                    for r in replanned
                    for reason in r.reasons
                )
            ),
            "decision_stored": int(
                any(
                    "\u91cd\u65b0\u89c4\u5212" in r.item.content
                    for r in engine.recall("重新规划 订机票", top_k=3)
                )
            ),
            "plan": replan_contents,
        },
        "plain_outcome_plan": {"plan": plan_contents},
    }
    ok = all(report["replan"][k] for k in
             ("ali_flight_at_end", "xiaobo_flight_kept_early",
              "replan_reason", "decision_stored"))
    report["all_ok"] = ok
    print("replan all_ok:", ok, flush=True)
    for k, v in report["replan"].items():
        if k != "plan":
            print(" ", k, v, flush=True)
    print("plain plan has ali flight at pos:",
          plan_contents.index(ALI_FLIGHT) if ALI_FLIGHT in plan_contents else None,
          flush=True)

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        answer = cloud_generate(
            "下面是重新规划后的参考计划。请为大壮写出调整后的旅行步骤计划，"
            "每步一行，避免失败过的步骤。\n\n"
            "上下文：\n" + "\n".join(f"- {c}" for c in replan_contents)
            + f"\n\n目标：{GOAL}"
        )
        report["llm"] = {
            "answer": answer,
            "avoids_ali_flight": int(ALI_FLIGHT not in answer),
            "keeps_xiaobo_flight": int("机票" in answer),
        }
        print("llm avoids ali flight:",
              report["llm"]["avoids_ali_flight"], flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
