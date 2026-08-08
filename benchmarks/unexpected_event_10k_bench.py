"""Unexpected-event retrieval at 10k (round 47).

30 steps have 5 successes + 1 ordinary failure; one target step (订机票)
has 5 successes + 1 UNEXPECTED failure (importance 0.9 + 意外 cue, from the
prediction-error mechanism). "哪个步骤出现过意外失败？" must surface the
target first; without the mechanism it is just one of 31 failures.
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

from reasoning_zh_10k_bench import generate_memories  # noqa: E402


TARGET_RECORD = "项目大壮京都旅行的步骤订机票执行失败（航班取消）。"
STEPS = ["订机票", "买相机", "打包箱子", "订餐厅", "买蛋糕", "收拾行李"]


def build_engine(use_mechanism: bool) -> MemoryEngine:
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
    # 30 ordinary steps: 5 successes + 1 failure (no alert)
    for i in range(30):
        step = STEPS[i % len(STEPS)]
        for _ in range(5):
            engine.remember(
                f"项目项目{i}的步骤{step}执行成功。",
                kind=MemoryKind.EPISODIC,
                source=source,
                cues=[f"项目{i}", step, "成功"],
                importance=0.75,
            )
        engine.remember(
            f"项目项目{i}的步骤{step}执行失败（备注{i}）。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[f"项目{i}", step, "失败"],
            importance=0.75,
        )
    # target step: 5 successes + 1 unexpected failure
    for _ in range(5):
        engine.remember(
            "项目大壮京都旅行的步骤订机票执行成功。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["大壮京都旅行", "订机票", "成功"],
            importance=0.75,
        )
    if use_mechanism:
        engine.remember(
            TARGET_RECORD,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["大壮京都旅行", "订机票", "失败", "意外"],
            importance=0.9,
        )
    else:
        engine.remember(
            TARGET_RECORD,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["大壮京都旅行", "订机票", "失败"],
            importance=0.75,
        )
    return engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "unexpected_event_10k_bench.json"),
    )
    args = parser.parse_args()
    report = {"memories": 0, "on": {}, "off": {}}
    for flag in (True, False):
        engine = build_engine(use_mechanism=flag)
        report["memories"] = len(engine.store.all_active())
        alert = engine.recall("哪个步骤出现过意外失败？", top_k=5)
        alert_ctx = [r.item.content for r in alert]
        plain = engine.recall("哪个步骤失败过？", top_k=5)
        plain_ctx = [r.item.content for r in plain]
        report["on" if flag else "off"] = {
            "alert_top1_target": int(
                bool(alert_ctx) and alert_ctx[0] == TARGET_RECORD
            ),
            "alert_in5_target": int(TARGET_RECORD in alert_ctx),
            "plain_top1_target": int(
                bool(plain_ctx) and plain_ctx[0] == TARGET_RECORD
            ),
            "alert_ctx": alert_ctx,
            "plain_ctx": plain_ctx,
        }
        print(
            ("on" if flag else "off"),
            "alert top1:", report["on" if flag else "off"]["alert_top1_target"],
            "in5:", report["on" if flag else "off"]["alert_in5_target"],
            "plain top1:", report["on" if flag else "off"]["plain_top1_target"],
            flush=True,
        )
        engine.close()
    print("memories:", report["memories"], flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
