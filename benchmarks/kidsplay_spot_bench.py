"""Kids-amusement-park spot-check (round 348): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月4日第一次带孩子去儿童乐园，办年卡1999元。",
        "kind": "episodic",
        "cues": ["2026-01-04", "年卡"],
    },
    {
        "content": "2026年1月11日第一次游玩完成。",
        "kind": "episodic",
        "cues": ["2026-01-11", "游玩"],
    },
    {
        "content": "乐园营业时间：早9点到晚8点。",
        "kind": "semantic",
        "cues": ["营业时间", "9点"],
    },
    {
        "content": "乐园电话 0791-8888-9999。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "游乐项目：海洋球池、蹦床、沙池、小火车。",
        "kind": "semantic",
        "cues": ["项目", "海洋球"],
    },
    {
        "content": "2026年2月2日预约2月15日生日派对。",
        "kind": "episodic",
        "cues": ["2026-02-02", "生日"],
    },
    {
        "content": "2026年2月15日生日派对完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "生日"],
    },
    {
        "content": "停车规则：消费满100元免费停车2小时。",
        "kind": "semantic",
        "cues": ["停车", "规则"],
    },
    {
        "content": "安全规则：3岁以下需家长陪同。",
        "kind": "semantic",
        "cues": ["安全", "规则"],
    },
    {
        "content": "2026年3月10日收到通知：3月25日春季主题活动。",
        "kind": "episodic",
        "cues": ["2026-03-10", "主题活动"],
    },
    {
        "content": "2026年3月25日活动完成。",
        "kind": "episodic",
        "cues": ["2026-03-25", "主题活动"],
    },
    {
        "content": "2026年4月8日预约4月21日周末游玩。",
        "kind": "episodic",
        "cues": ["2026-04-08", "游玩"],
    },
    {
        "content": "2026年4月21日周末游玩完成。",
        "kind": "episodic",
        "cues": ["2026-04-21", "游玩"],
    },
    {
        "content": "2026年5月10日收到通知：5月25日六一活动预热。",
        "kind": "episodic",
        "cues": ["2026-05-10", "六一"],
    },
    {
        "content": "2026年5月25日六一活动预热完成。",
        "kind": "episodic",
        "cues": ["2026-05-25", "六一"],
    },
    {
        "content": "2026年6月12日预约6月26日暑期卡办理。",
        "kind": "episodic",
        "cues": ["2026-06-12", "暑期卡"],
    },
    {
        "content": "2026年6月26日办理暑期卡。",
        "kind": "episodic",
        "cues": ["2026-06-26", "暑期卡"],
    },
    {
        "content": "2026年7月10日收到通知：7月25日夏日水乐园开放。",
        "kind": "episodic",
        "cues": ["2026-07-10", "水乐园"],
    },
    {
        "content": "2026年8月3日预约8月17日下次游玩。",
        "kind": "episodic",
        "cues": ["2026-08-03", "游玩"],
    },
    {
        "content": "2026年8月10日收到提醒：8月28日年卡续卡优惠截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "续卡"],
    },
]


QUESTIONS = [
    {
        "dim": "首次办卡",
        "q": "儿童乐园年卡第一次什么时候办的？",
        "answer": "1月4日",
        "terms": ["4"],
    },
    {
        "dim": "年卡价格",
        "q": "年卡多少钱？",
        "answer": "1999元",
        "terms": ["1999"],
    },
    {
        "dim": "下次游玩",
        "q": "下次游玩是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "乐园几点关门？",
        "answer": "晚8点",
        "terms": ["8"],
    },
    {
        "dim": "电话",
        "q": "儿童乐园电话多少？",
        "answer": "0791-8888-9999",
        "terms": ["9999"],
    },
    {
        "dim": "游乐项目",
        "q": "乐园有哪些游乐项目？",
        "answer": "海洋球池、蹦床、沙池、小火车",
        "terms": ["蹦床"],
    },
    {
        "dim": "停车规则",
        "q": "消费多少可以免费停车2小时？",
        "answer": "100元",
        "terms": ["100"],
    },
    {
        "dim": "安全规则",
        "q": "几岁以下需要家长陪同？",
        "answer": "3岁以下",
        "terms": ["3"],
    },
    {
        "dim": "生日派对",
        "q": "生日派对什么时候办的？",
        "answer": "2月15日",
        "terms": ["15"],
    },
    {
        "dim": "续卡优惠",
        "q": "年卡续卡优惠什么时候截止？",
        "answer": "8月28日",
        "terms": ["28"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="儿童乐园",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="kidsplay_mem0db",
        out_name="kidsplay_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
