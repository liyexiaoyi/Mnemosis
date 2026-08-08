"""Outcome evidence at 10k project history (round 37).

20 projects each have an outcome record; the three target projects' failure
records were confirmed twice (evidence_count=2) while same-step rivals have
one confirmation. Asks "哪个项目的订机票环节出过问题?" etc. Evidence
weighting should rank the twice-confirmed record first at 10k scale.
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


TARGETS = [
    {
        "q": "哪个项目的订机票环节出过问题？",
        "record": "项目大壮京都旅行的步骤订机票执行失败（航班取消）。",
        "key": "大壮",
    },
    {
        "q": "哪个项目的打包箱子环节出过问题？",
        "record": "项目强强搬家的步骤打包箱子执行失败（箱子不够）。",
        "key": "强强",
    },
    {
        "q": "哪个项目的订餐厅环节出过问题？",
        "record": "项目琳琳生日派对的步骤订餐厅执行失败（餐厅满座）。",
        "key": "琳琳",
    },
]

STEPS = ["订机票", "买相机", "打包箱子", "订餐厅", "买蛋糕", "收拾行李"]


def build_engine(use_evidence: bool) -> MemoryEngine:
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
    # rival outcome records (evidence 1), inserted before targets
    rival_projects = [f"项目{i}" for i in range(1, 21)]
    for i, p in enumerate(rival_projects, start=1):
        step = STEPS[i % len(STEPS)]
        engine.remember(
            f"{p}的步骤{step}执行失败（备注{p}）。",
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[p, step],
            evidence_count=1,
        )
    # targets (evidence 2 in the ON condition, 1 in OFF)
    for t in TARGETS:
        engine.remember(
            t["record"],
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=["大壮京都旅行" if "大壮" in t["record"] else
                  "强强搬家" if "强强" in t["record"] else
                  "琳琳生日派对", "订机票" if "订机票" in t["record"] else
                  "打包箱子" if "打包箱子" in t["record"] else "订餐厅"],
            evidence_count=2 if use_evidence else 1,
        )
    return engine


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "outcome_evidence_10k_bench.json"),
    )
    args = parser.parse_args()
    report = {"memories": 0, "on": {}, "off": {}}
    for flag in (True, False):
        engine = build_engine(use_evidence=flag)
        report["memories"] = len(engine.store.all_active())
        stats = {"top1_target": 0, "target_in5": 0, "n": len(TARGETS)}
        rows = []
        for t in TARGETS:
            results = engine.recall(t["q"], top_k=5)
            contents = [r.item.content for r in results]
            rows.append(
                {
                    "question": t["q"],
                    "top1": contents[0] if contents else "",
                    "context": contents,
                }
            )
            stats["top1_target"] += int(
                bool(contents) and contents[0] == t["record"]
            )
            stats["target_in5"] += int(t["record"] in contents)
        report["on" if flag else "off"] = {"stats": stats, "rows": rows}
        print(
            ("on" if flag else "off"),
            "top1:", stats["top1_target"], "/", stats["n"],
            "in5:", stats["target_in5"], "/", stats["n"],
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
