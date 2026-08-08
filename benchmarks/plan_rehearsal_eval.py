"""Plan-rehearsal eval (round 244, constructive episodic simulation).

10 stores. Each store: two people's travel plans plus outcome records
(阿丽's flight step fails; 小波's steps succeed). plan_rehearsal must
pre-play the plan, flag the weakest step and stay graceful on unknown
goals.
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
from mnemosis.mcp_server import MCPServer  # noqa: E402
from mnemosis.types import MemoryKind, SourceRecord, SourceType  # noqa: E402


def _store(seed: int):
    engine = MemoryEngine()
    source = SourceRecord(origin=SourceType.USER)
    steps = (
        ("阿丽在2026年4月1日订了去京都的机票。", "阿丽", "2026-04-01"),
        ("阿丽在2026年4月2日买了相机。", "阿丽", "2026-04-02"),
        ("小波在2026年5月1日订了去京都的机票。", "小波", "2026-05-01"),
        ("小波在2026年5月2日买了相机。", "小波", "2026-05-02"),
    )
    for content, person, iso in steps:
        engine.remember(
            content,
            kind=MemoryKind.EPISODIC,
            source=source,
            cues=[person, iso],
        )
    for _ in range(seed % 3 + 1):
        engine.record_outcome(
            "阿丽旅行", "订机票", success=False, note="航班取消"
        )
    engine.record_outcome("小波旅行", "订机票", success=True)
    engine.record_outcome("小波旅行", "买相机", success=True)
    return engine, MCPServer(engine=engine)


def _run() -> dict:
    steps_ok = prob_ok = weakest_ok = overall_ok = advice_ok = empty_ok = (
        fields_ok
    ) = mcp_ok = 0
    for seed in range(10):
        engine, server = _store(seed)
        report = engine.plan_rehearsal(
            "大壮想去京都旅行，参考阿丽和小波谁的计划更好？",
            top_k=8,
        )
        steps_ok += int(report["step_count"] == 4)
        prob_ok += int(
            all(
                0 <= s["success_probability"] <= 1
                and s["source"] in ("records", "consolidated")
                for s in report["steps"]
            )
        )
        weakest_ok += int(
            report["weakest_step"] is not None
            and report["weakest_step"]["success_probability"]
            == min(s["success_probability"] for s in report["steps"])
            and "阿丽" in report["weakest_step"]["step"]
        )
        overall_ok += int(
            report["overall_success_probability"]
            == min(s["success_probability"] for s in report["steps"])
        )
        advice_ok += int("预演" in report["rehearsal_advice"])
        empty = MemoryEngine().plan_rehearsal(
            "想从没出现过的奇怪地方旅行"
        )
        empty_ok += int(
            empty["step_count"] == 0
            and empty["weakest_step"] is None
            and "预演" in empty["rehearsal_advice"]
        )
        fields_ok += int(
            {
                "goal",
                "steps",
                "step_count",
                "weakest_step",
                "overall_success_probability",
                "fallback",
                "rehearsal_advice",
            }
            <= set(report)
        )
        via_mcp = server._call_tool(
            "plan_rehearsal",
            {
                "goal": "大壮想去京都旅行，参考阿丽和小波谁的计划更好？",
                "top_k": 8,
            },
        )
        mcp_ok += int(
            via_mcp["step_count"] == 4
            and via_mcp["weakest_step"] is not None
        )
    return {
        "stores": 10,
        "steps_ok": steps_ok,
        "prob_ok": prob_ok,
        "weakest_ok": weakest_ok,
        "overall_ok": overall_ok,
        "advice_ok": advice_ok,
        "empty_ok": empty_ok,
        "fields_ok": fields_ok,
        "mcp_ok": mcp_ok,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        default=os.path.join(_BENCH, "results", "plan_rehearsal_eval.json"),
    )
    args = parser.parse_args()
    report = _run()
    report["all_ok"] = all(
        v == 10 for k, v in report.items() if k != "stores"
    )
    print(report, flush=True)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
