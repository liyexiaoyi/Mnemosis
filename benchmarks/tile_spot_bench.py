"""Renovation-tile spot-check (round 340): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月9日购买客厅瓷砖，800x800规格，共4200元。",
        "kind": "episodic",
        "cues": ["2026-01-09", "瓷砖"],
    },
    {
        "content": "2026年1月15日瓷砖送货到工地。",
        "kind": "episodic",
        "cues": ["2026-01-15", "送货"],
    },
    {
        "content": "瓷砖门店营业时间：早9点到晚6点。",
        "kind": "semantic",
        "cues": ["营业时间", "9点"],
    },
    {
        "content": "瓷砖门店电话 0592-8888-6666。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "2026年2月1日预约2月14日瓦工师傅进场。",
        "kind": "episodic",
        "cues": ["2026-02-01", "瓦工"],
    },
    {
        "content": "2026年2月14日瓦工师傅进场施工。",
        "kind": "episodic",
        "cues": ["2026-02-14", "瓦工"],
    },
    {
        "content": "2026年2月25日客厅瓷砖铺贴完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "铺贴"],
    },
    {
        "content": "2026年3月6日发现剩余瓷砖10片。",
        "kind": "episodic",
        "cues": ["2026-03-06", "余料"],
    },
    {
        "content": "2026年3月12日预约3月25日补货5片同款瓷砖。",
        "kind": "episodic",
        "cues": ["2026-03-12", "补货"],
    },
    {
        "content": "2026年3月25日补货送达。",
        "kind": "episodic",
        "cues": ["2026-03-25", "补货"],
    },
    {
        "content": "2026年4月8日收到通知：4月22日瓷砖验收。",
        "kind": "episodic",
        "cues": ["2026-04-08", "验收"],
    },
    {
        "content": "2026年4月22日验收完成，空鼓率合格。",
        "kind": "episodic",
        "cues": ["2026-04-22", "验收"],
    },
    {
        "content": "2026年5月6日购买卫生间瓷砖，300x600规格，共1800元。",
        "kind": "episodic",
        "cues": ["2026-05-06", "卫生间"],
    },
    {
        "content": "2026年5月20日卫生间瓷砖送货。",
        "kind": "episodic",
        "cues": ["2026-05-20", "送货"],
    },
    {
        "content": "2026年6月2日卫生间瓷砖铺贴完成。",
        "kind": "episodic",
        "cues": ["2026-06-02", "铺贴"],
    },
    {
        "content": "质保说明：瓷砖质保5年。",
        "kind": "semantic",
        "cues": ["质保", "5年"],
    },
    {
        "content": "2026年7月4日收到通知：7月18日阳台瓷砖选购会。",
        "kind": "episodic",
        "cues": ["2026-07-04", "选购会"],
    },
    {
        "content": "2026年7月18日选购会完成，选定阳台砖。",
        "kind": "episodic",
        "cues": ["2026-07-18", "选购会"],
    },
    {
        "content": "2026年8月3日预约8月16日阳台瓷砖送货。",
        "kind": "episodic",
        "cues": ["2026-08-03", "阳台砖"],
    },
    {
        "content": "2026年8月10日收到提醒：8月24日余料回收活动。",
        "kind": "episodic",
        "cues": ["2026-08-10", "余料回收"],
    },
]


QUESTIONS = [
    {
        "dim": "首次购买",
        "q": "客厅瓷砖第一次什么时候买的？",
        "answer": "1月9日",
        "terms": ["9"],
    },
    {
        "dim": "瓷砖价格",
        "q": "客厅瓷砖多少钱？",
        "answer": "4200元",
        "terms": ["4200"],
    },
    {
        "dim": "下次送货",
        "q": "下次瓷砖送货是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "营业时间",
        "q": "瓷砖门店几点开门？",
        "answer": "早9点",
        "terms": ["9"],
    },
    {
        "dim": "门店电话",
        "q": "瓷砖门店电话多少？",
        "answer": "0592-8888-6666",
        "terms": ["6666"],
    },
    {
        "dim": "瓷砖规格",
        "q": "客厅瓷砖是什么规格？",
        "answer": "800x800",
        "terms": ["800"],
    },
    {
        "dim": "余料数量",
        "q": "客厅瓷砖剩下多少片？",
        "answer": "10片",
        "terms": ["10"],
    },
    {
        "dim": "瓦工进场",
        "q": "瓦工师傅什么时候进场的？",
        "answer": "2月14日",
        "terms": ["14"],
    },
    {
        "dim": "质保",
        "q": "瓷砖质保几年？",
        "answer": "5年",
        "terms": ["5"],
    },
    {
        "dim": "验收",
        "q": "瓷砖验收什么时候？",
        "answer": "4月22日",
        "terms": ["22"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="装修瓷砖",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="tile_mem0db",
        out_name="tile_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
