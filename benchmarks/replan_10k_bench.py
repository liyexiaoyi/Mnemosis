"""Re-planning at 10k project history (round 45).

阿丽's flight step failed twice, 小波's steps all succeeded, plus 30 rival
projects with the same step words buried under ~10k noise. replan() must
move ONLY 阿丽's failed flight to the end at scale.
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

from reasoning_zh_10k_bench import generate_memories

from mnemosis import MemoryEngine
from mnemosis.types import MemoryKind, SourceRecord, SourceType

GOAL = "大壮想去京都旅行，参考阿丽和小波"
ALI_FLIGHT = "阿丽在2026年4月1日订了去京都的机票。"
XIAOBO_FLIGHT = "小波在2026年5月1日订了去京都的机票。"


def build_engine() -> MemoryEngine:
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    for content in generate_memories():
        cue = content.split("最")[0].split("比")[0].split("买")[0]
        engine.remember(
            content,
            kind=MemoryKind.SEMANTIC,
            source=source,
            cues=[cue],
            importance=0.7,
        )
    for i in range(1, 31):
        person = f"人物{i}"
        engine.remember(
            f"{person}在2026年3月1日订了去京都的机票。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, "2026-03-01"],
        )
        engine.remember(
            f"项目{person}旅行的步骤订机票执行失败（备注{i}）。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person + "旅行", "订机票", "失败"],
            evidence_count=1,
        )
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
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "replan_10k_bench.json"),
    )
    args = parser.parse_args()
    engine = build_engine()
    replanned = engine.replan(GOAL, "订机票")
    contents = [r.item.content for r in replanned]
    report = {
        "memories": len(engine.store.all_active()),
        "ali_flight_at_end": int(
            ALI_FLIGHT in contents
            and contents.index(ALI_FLIGHT) == len(contents) - 1
        ),
        "xiaobo_flight_before": int(
            XIAOBO_FLIGHT in contents
            and ALI_FLIGHT in contents
            and contents.index(XIAOBO_FLIGHT) < contents.index(ALI_FLIGHT)
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
        "plan_len": len(contents),
        "plan": contents,
    }
    report["all_ok"] = all(
        report[k] for k in ("ali_flight_at_end", "xiaobo_flight_before",
                            "replan_reason", "decision_stored")
    )
    print("memories:", report["memories"], "all_ok:", report["all_ok"],
          "plan_len:", report["plan_len"], flush=True)
    for k in ("ali_flight_at_end", "xiaobo_flight_before",
              "replan_reason", "decision_stored"):
        print(" ", k, report[k], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    engine.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
