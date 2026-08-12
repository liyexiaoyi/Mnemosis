"""Outcome-aware plan choice at 10k project history (round 39).

Two reference trip plans buried under ~10k noise: 阿丽's 订机票 failed
twice, 小波's steps all succeeded; 30 rival projects also have outcome
records with the same step words. The goal asks which plan is more
reliable; outcome-aware reranking must surface 小波's steps first.
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys

_BENCH = os.path.dirname(os.path.abspath(__file__))
_SRC = os.path.normpath(os.path.join(_BENCH, "..", "src"))
sys.path.insert(0, _BENCH)
sys.path.insert(0, _SRC)

from reasoning_zh_10k_bench import generate_memories

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

GOAL = "大壮想去京都旅行，参考阿丽和小波谁的计划更好？"
ALI_STEPS = [
    "阿丽在2026年4月1日订了去京都的机票。",
    "阿丽在2026年4月2日买了相机。",
]
XIAOBO_STEPS = [
    "小波在2026年5月1日订了去京都的机票。",
    "小波在2026年5月2日买了相机。",
]


def build_engine(noise_scale: float = 1.0, seed: int = 27) -> MemoryEngine:
    """Build the benchmark engine.

    ``noise_scale`` controls how much of the background noise is kept
    (CI uses a small ratio for speed); the reference plans and rival
    projects are always injected in full. A fixed-seed random sample is
    used instead of a head slice so the reduced store still represents a
    uniform mix of the noise distribution.
    """
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    noise = generate_memories()
    # Reference plans are injected separately below, but keep them out of
    # the sampled noise explicitly so a future generator change cannot
    # accidentally drop them from the reduced CI store.
    key_contents = set(XIAOBO_STEPS) | set(ALI_STEPS)
    noise = [
        content for content in noise if content not in key_contents
    ]
    sample_size = max(1, int(len(noise) * noise_scale))
    sample = random.Random(seed).sample(
        noise, min(sample_size, len(noise))
    )
    for content in sample:
        cue = content.split("最")[0].split("比")[0].split("买")[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    # 30 rival projects with same-step outcome records
    for i in range(1, 31):
        person = f"人物{i}"
        step = "订机票" if i % 2 else "买相机"
        engine.remember(
            f"{person}在2026年3月1日订了去京都的机票。"
            if i % 2
            else f"{person}在2026年3月1日买了相机。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, "2026-03-01"],
        )
        engine.remember(
            f"项目{person}旅行的步骤{step}执行失败（备注{i}）。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person + "旅行", step, "失败"],
            evidence_count=1,
        )
    # reference plans
    for content, person, iso in (
        (ALI_STEPS[0], "阿丽", "2026-04-01"),
        (ALI_STEPS[1], "阿丽", "2026-04-02"),
        (XIAOBO_STEPS[0], "小波", "2026-05-01"),
        (XIAOBO_STEPS[1], "小波", "2026-05-02"),
    ):
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, iso],
        )
    # outcomes: 阿丽 订机票 failed twice; 小波 all success
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
        default=os.path.join(_BENCH, "results", "plan_choice_10k_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    report = {"memories": len(engine.store.all_active()), "on": {}, "off": {}}
    print("memories:", report["memories"], flush=True)
    for aware in (True, False):
        plan = engine.plan_for_goal(GOAL, top_k=10, outcome_aware=aware)
        contents = [r.item.content for r in plan]
        xiaobo_idx = (
            contents.index(XIAOBO_STEPS[0]) if XIAOBO_STEPS[0] in contents else 99
        )
        ali_idx = contents.index(ALI_STEPS[0]) if ALI_STEPS[0] in contents else 99
        report["on" if aware else "off"] = {
            "successful_plan_first": int(xiaobo_idx < ali_idx),
            "ali_step_in": int(ALI_STEPS[0] in contents),
            "xiaobo_step_in": int(XIAOBO_STEPS[0] in contents),
            "plan": contents,
        }
        print(
            ("on" if aware else "off"),
            "successful first:", report["on" if aware else "off"]["successful_plan_first"],
            "ali_in:", report["on" if aware else "off"]["ali_step_in"],
            "xiaobo_in:", report["on" if aware else "off"]["xiaobo_step_in"],
            flush=True,
        )

    if args.llm:
        from cloud_qwen_matrix import cloud_generate

        report["llm"] = []
        for aware in (True, False):
            contents = report["on" if aware else "off"]["plan"]
            outcome_records = [
                r.item.content
                for r in engine.recall("执行成功 执行失败", top_k=8)
            ]
            answer = cloud_generate(
                "下面是两个参考计划和执行记录。给大壮做京都旅行计划，"
                "参考谁的计划更可靠？只回答人名。\n\n"
                "参考计划：\n" + "\n".join(f"- {c}" for c in contents)
                + "\n\n执行记录：\n"
                + "\n".join(f"- {c}" for c in outcome_records)
                + f"\n\n问题：{GOAL}"
            )
            ok = int("小波" in answer and "阿丽" not in answer)
            report["llm"].append(
                {"condition": "on" if aware else "off",
                 "answer": answer, "picks_successful": ok}
            )
            print(("llm-on" if aware else "llm-off"), "picks 小波:", ok,
                  "|", answer[:40], flush=True)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
