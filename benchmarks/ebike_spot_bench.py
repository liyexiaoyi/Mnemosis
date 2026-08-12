"""E-bike spot-check (round 306): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买电动车：雅迪 3299 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "电动车"],
    },
    {
        "content": "2026年1月20日上牌完成。",
        "kind": "episodic",
        "cues": ["2026-01-20", "上牌"],
    },
    {
        "content": "2026年2月1日第一次充电。",
        "kind": "episodic",
        "cues": ["2026-02-01", "充电"],
    },
    {
        "content": "2026年2月15日换头盔：全盔 299 元。",
        "kind": "episodic",
        "cues": ["2026-02-15", "头盔"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日保养。",
        "kind": "episodic",
        "cues": ["2026-03-01", "保养"],
    },
    {
        "content": "2026年3月15日保养完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "保养"],
    },
    {
        "content": "2026年4月1日轮胎扎破，4 月 5 日补胎。",
        "kind": "episodic",
        "cues": ["2026-04-01", "补胎"],
    },
    {
        "content": "2026年4月5日补胎完成。",
        "kind": "episodic",
        "cues": ["2026-04-05", "补胎"],
    },
    {
        "content": "2026年5月1日预约 5 月 10 日换电池。",
        "kind": "episodic",
        "cues": ["2026-05-01", "电池"],
    },
    {
        "content": "2026年5月10日换电池：600 元。",
        "kind": "episodic",
        "cues": ["2026-05-10", "电池"],
    },
    {
        "content": "2026年6月1日刹车异响，6 月 5 日修。",
        "kind": "episodic",
        "cues": ["2026-06-01", "刹车"],
    },
    {
        "content": "2026年6月5日修好。",
        "kind": "episodic",
        "cues": ["2026-06-05", "刹车"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日年检。",
        "kind": "episodic",
        "cues": ["2026-07-01", "年检"],
    },
    {
        "content": "2026年7月10日年检通过。",
        "kind": "episodic",
        "cues": ["2026-07-10", "年检"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日贴膜。",
        "kind": "episodic",
        "cues": ["2026-08-01", "贴膜"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日充电器换新。",
        "kind": "episodic",
        "cues": ["2026-08-05", "充电器"],
    },
    {
        "content": "电动车店电话 400-555-8888。",
        "kind": "semantic",
        "cues": ["电动车店", "电话"],
    },
    {
        "content": "停车位：B1-08。",
        "kind": "semantic",
        "cues": ["停车位", "B1"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日免费检修日。",
        "kind": "episodic",
        "cues": ["2026-08-08", "检修日"],
    },
]


QUESTIONS = [
    {
        "dim": "车辆信息",
        "q": "电动车多少钱？什么牌子？",
        "answer": "雅迪，3299元",
        "terms": ["3299"],
    },
    {
        "dim": "保养记录",
        "q": "上次保养是什么时候？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "电池更换",
        "q": "电池什么时候换的？多少钱？",
        "answer": "5月10日，600元",
        "terms": ["600"],
    },
    {
        "dim": "未来安排",
        "q": "下次贴膜是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "头盔价格",
        "q": "头盔多少钱？",
        "answer": "299元",
        "terms": ["299"],
    },
    {
        "dim": "刹车维修",
        "q": "刹车什么问题？什么时候修的？",
        "answer": "异响，6月5日",
        "terms": ["异响"],
    },
    {
        "dim": "年检记录",
        "q": "年检通过了吗？什么时候？",
        "answer": "7月10日通过",
        "terms": ["通过"],
    },
    {
        "dim": "停车位",
        "q": "电动车停哪？",
        "answer": "B1-08",
        "terms": ["B1"],
    },
    {
        "dim": "充电器提醒",
        "q": "充电器什么时候换新？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "检修日",
        "q": "免费检修日什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="电动车维护",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="ebike_mem0db",
        out_name="ebike_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
