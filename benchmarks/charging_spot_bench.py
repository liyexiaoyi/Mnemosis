"""EV-charging-pile spot-check (round 342): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月8日安装家用充电桩，安装费800元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "安装"],
    },
    {
        "content": "2026年1月15日第一次用充电桩充电。",
        "kind": "episodic",
        "cues": ["2026-01-15", "充电"],
    },
    {
        "content": "充电桩位置：小区地下车库B区。",
        "kind": "semantic",
        "cues": ["位置", "车库"],
    },
    {
        "content": "充电桩功率：7千瓦。",
        "kind": "semantic",
        "cues": ["功率", "7千瓦"],
    },
    {
        "content": "售后电话 400-900-5678。",
        "kind": "semantic",
        "cues": ["售后", "电话"],
    },
    {
        "content": "电费规则：低谷时段每度0.3元。",
        "kind": "semantic",
        "cues": ["电费", "低谷"],
    },
    {
        "content": "2026年2月10日收到通知：2月25日充电桩巡检。",
        "kind": "episodic",
        "cues": ["2026-02-10", "巡检"],
    },
    {
        "content": "2026年2月25日巡检完成，设备正常。",
        "kind": "episodic",
        "cues": ["2026-02-25", "巡检"],
    },
    {
        "content": "2026年3月15日购买充电桩保险，年费180元。",
        "kind": "episodic",
        "cues": ["2026-03-15", "保险"],
    },
    {
        "content": "2026年4月6日遇到充电故障，联系售后处理。",
        "kind": "episodic",
        "cues": ["2026-04-06", "故障"],
    },
    {
        "content": "2026年4月10日故障修复完成。",
        "kind": "episodic",
        "cues": ["2026-04-10", "修复"],
    },
    {
        "content": "2026年5月12日预约5月25日升级充电枪。",
        "kind": "episodic",
        "cues": ["2026-05-12", "升级"],
    },
    {
        "content": "2026年5月25日升级完成。",
        "kind": "episodic",
        "cues": ["2026-05-25", "升级"],
    },
    {
        "content": "2026年6月8日收到通知：6月20日充电桩安全检查。",
        "kind": "episodic",
        "cues": ["2026-06-08", "安全检查"],
    },
    {
        "content": "2026年6月20日安全检查通过。",
        "kind": "episodic",
        "cues": ["2026-06-20", "安全检查"],
    },
    {
        "content": "2026年7月5日收到通知：7月21日充电桩APP改版。",
        "kind": "episodic",
        "cues": ["2026-07-05", "APP"],
    },
    {
        "content": "2026年7月21日APP改版完成。",
        "kind": "episodic",
        "cues": ["2026-07-21", "APP"],
    },
    {
        "content": "2026年8月2日预约8月15日充电桩保养。",
        "kind": "episodic",
        "cues": ["2026-08-02", "保养"],
    },
    {
        "content": "2026年8月10日收到提醒：8月22日保险续费。",
        "kind": "episodic",
        "cues": ["2026-08-10", "保险"],
    },
    {
        "content": "充电记录：7月共充电280度。",
        "kind": "semantic",
        "cues": ["充电", "280度"],
    },
]


QUESTIONS = [
    {
        "dim": "安装时间",
        "q": "充电桩第一次什么时候安装的？",
        "answer": "1月8日",
        "terms": ["8"],
    },
    {
        "dim": "安装费用",
        "q": "充电桩安装费多少钱？",
        "answer": "800元",
        "terms": ["800"],
    },
    {
        "dim": "下次保养",
        "q": "下次充电桩保养是什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "充电桩位置",
        "q": "充电桩装在哪里？",
        "answer": "小区地下车库B区",
        "terms": ["车库"],
    },
    {
        "dim": "售后电话",
        "q": "充电桩售后电话多少？",
        "answer": "400-900-5678",
        "terms": ["5678"],
    },
    {
        "dim": "功率",
        "q": "充电桩功率多大？",
        "answer": "7千瓦",
        "terms": ["7"],
    },
    {
        "dim": "低谷电费",
        "q": "低谷时段一度电多少钱？",
        "answer": "0.3元",
        "terms": ["0.3"],
    },
    {
        "dim": "巡检",
        "q": "充电桩巡检什么时候？",
        "answer": "2月25日",
        "terms": ["25"],
    },
    {
        "dim": "保险续费",
        "q": "保险什么时候续费？",
        "answer": "8月22日",
        "terms": ["22"],
    },
    {
        "dim": "故障处理",
        "q": "充电桩故障怎么处理？",
        "answer": "联系售后",
        "terms": ["售后"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="汽车充电桩",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="charging_mem0db",
        out_name="charging_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
