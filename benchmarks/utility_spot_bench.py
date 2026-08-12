"""Utilities-payment spot-check (round 318): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日绑定水费户号。",
        "kind": "episodic",
        "cues": ["2026-01-10", "水费"],
    },
    {
        "content": "2026年1月20日缴电费：1 月 25 日。",
        "kind": "episodic",
        "cues": ["2026-01-20", "电费"],
    },
    {
        "content": "2026年1月25日电费 186 元。",
        "kind": "episodic",
        "cues": ["2026-01-25", "电费"],
    },
    {
        "content": "2026年2月1日缴水费：58 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "水费"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日燃气抄表。",
        "kind": "episodic",
        "cues": ["2026-02-15", "燃气"],
    },
    {
        "content": "2026年2月25日抄表完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "燃气"],
    },
    {
        "content": "2026年3月1日缴物业费：3 月 10 日。",
        "kind": "episodic",
        "cues": ["2026-03-01", "物业费"],
    },
    {
        "content": "2026年3月10日物业费 800 元。",
        "kind": "episodic",
        "cues": ["2026-03-10", "物业费"],
    },
    {
        "content": "2026年4月1日预约 4 月 15 日换燃气表。",
        "kind": "episodic",
        "cues": ["2026-04-01", "燃气表"],
    },
    {
        "content": "2026年4月15日换表完成。",
        "kind": "episodic",
        "cues": ["2026-04-15", "燃气表"],
    },
    {
        "content": "2026年5月1日缴暖气费：5 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-05-01", "暖气"],
    },
    {
        "content": "2026年5月20日暖气费 1200 元。",
        "kind": "episodic",
        "cues": ["2026-05-20", "暖气"],
    },
    {
        "content": "2026年6月1日预约 6 月 15 日水表检查。",
        "kind": "episodic",
        "cues": ["2026-06-01", "水表"],
    },
    {
        "content": "2026年6月15日检查完成。",
        "kind": "episodic",
        "cues": ["2026-06-15", "水表"],
    },
    {
        "content": "2026年7月1日缴垃圾费：7 月 10 日。",
        "kind": "episodic",
        "cues": ["2026-07-01", "垃圾费"],
    },
    {
        "content": "2026年7月10日垃圾费 30 元。",
        "kind": "episodic",
        "cues": ["2026-07-10", "垃圾费"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日缴季度电费。",
        "kind": "episodic",
        "cues": ["2026-08-01", "电费"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日燃气费。",
        "kind": "episodic",
        "cues": ["2026-08-05", "燃气费"],
    },
    {
        "content": "缴费客服 400-666-0000。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "缴费日：每月 15 日。",
        "kind": "semantic",
        "cues": ["缴费日"],
    },
]


QUESTIONS = [
    {
        "dim": "电费",
        "q": "上次电费多少钱？",
        "answer": "186元",
        "terms": ["186"],
    },
    {
        "dim": "水费",
        "q": "上次水费多少钱？",
        "answer": "58元",
        "terms": ["58"],
    },
    {
        "dim": "物业费",
        "q": "物业费什么时候缴的？多少钱？",
        "answer": "3月10日，800元",
        "terms": ["800"],
    },
    {
        "dim": "未来安排",
        "q": "下次缴电费是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "燃气表",
        "q": "燃气表什么时候换的？",
        "answer": "4月15日",
        "terms": ["15"],
    },
    {
        "dim": "暖气费",
        "q": "暖气费多少钱？",
        "answer": "1200元",
        "terms": ["1200"],
    },
    {
        "dim": "垃圾费",
        "q": "垃圾费多少钱？",
        "answer": "30元",
        "terms": ["30"],
    },
    {
        "dim": "缴费客服",
        "q": "缴费客服电话多少？",
        "answer": "400-666-0000",
        "terms": ["0000"],
    },
    {
        "dim": "缴费日",
        "q": "每月几号缴费？",
        "answer": "15日",
        "terms": ["15"],
    },
    {
        "dim": "燃气费",
        "q": "燃气费什么时候缴？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="水电燃气",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="utility_mem0db",
        out_name="utility_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
