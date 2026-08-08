"""Outcome-aware plan choice benchmark (round 38, law of effect).

Two reference trip plans: 阿丽's 订机票 failed twice, 小波's steps all
succeeded. A new goal asks which plan is better. With outcome-aware
reranking the successful plan's steps surface first and the cloud model
should pick 小波; without it, ordering is chronological and the choice is
ambiguous.
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


GOAL = "大壮想去京都旅行，参考阿丽和小波谁的计划更好？"
STEPS = [
    ("阿丽在2026年4月1日订了去京都的机票。", "阿丽", "2026-04-01"),
    ("阿丽在2026年4月2日买了相机。", "阿丽", "2026-04-02"),
    ("小波在2026年5月1日订了去京都的机票。", "小波", "2026-05-01"),
    ("小波在2026年5月2日买了相机。", "小波", "2026-05-02"),
]


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content, person, iso in STEPS:
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
        default=os.path.join(_BENCH, "results", "plan_choice_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    report: dict = {}
    for aware in (True, False):
        plan = engine.plan_for_goal(GOAL, top_k=8, outcome_aware=aware)
        contents = [r.item.content for r in plan]
        xiaobo_first = int(
            contents.index("小波在2026年5月1日订了去京都的机票。")
            < contents.index("阿丽在2026年4月1日订了去京都的机票。")
        )
        report["on" if aware else "off"] = {
            "successful_plan_first": xiaobo_first,
            "plan": contents,
        }
        print(
            ("on" if aware else "off"),
            "successful plan first:", xiaobo_first,
            flush=True,
        )

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        report["llm"] = []
        for aware in (True, False):
            contents = report["on" if aware else "off"]["plan"]
            outcome_records = [
                r.item.content
                for r in engine.recall("执行成功 执行失败", top_k=6)
            ]
            answer = cloud_generate(
                "下面是两个参考计划，和它们的执行记录。请判断：给大壮做京都旅行计划，"
                "参考谁的计划更可靠？只回答人名。\n\n"
                f"参考计划：\n" + "\n".join(f"- {c}" for c in contents)
                + f"\n\n执行记录：\n"
                + "\n".join(f"- {c}" for c in outcome_records)
                + f"\n\n问题：{GOAL}"
            )
            ok = int("小波" in answer and "阿丽" not in answer)
            report["llm"].append(
                {"condition": "on" if aware else "off",
                 "answer": answer, "picks_successful": ok}
            )
            print(
                ("llm-on" if aware else "llm-off"),
                "picks 小波:", ok, "|", answer[:40],
                flush=True,
            )

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
