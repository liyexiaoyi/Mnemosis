"""Car-rental spot-check (round 356): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月7日第一次租车，经济型轿车日租180元。",
        "kind": "episodic",
        "cues": ["2026-01-07", "租车"],
    },
    {
        "content": "2026年1月10日还车完成。",
        "kind": "episodic",
        "cues": ["2026-01-10", "还车"],
    },
    {
        "content": "租车门店营业时间：早8点到晚9点。",
        "kind": "semantic",
        "cues": ["营业时间", "8点"],
    },
    {
        "content": "租车门店电话 0898-6666-7777。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "车型：经济型、舒适型、SUV、商务车。",
        "kind": "semantic",
        "cues": ["车型", "SUV"],
    },
    {
        "content": "2026年2月3日预约2月15日SUV租车。",
        "kind": "episodic",
        "cues": ["2026-02-03", "SUV"],
    },
    {
        "content": "2026年2月15日取SUV，日租350元。",
        "kind": "episodic",
        "cues": ["2026-02-15", "SUV"],
    },
    {
        "content": "2026年2月18日还车完成。",
        "kind": "episodic",
        "cues": ["2026-02-18", "还车"],
    },
    {
        "content": "保险说明：基础保险已含，不计免赔需另购。",
        "kind": "semantic",
        "cues": ["保险", "说明"],
    },
    {
        "content": "油量规则：满油取车，满油还车。",
        "kind": "semantic",
        "cues": ["油量", "规则"],
    },
    {
        "content": "2026年3月10日收到通知：3月24日违章处理提醒。",
        "kind": "episodic",
        "cues": ["2026-03-10", "违章"],
    },
    {
        "content": "2026年3月24日处理违章完成。",
        "kind": "episodic",
        "cues": ["2026-03-24", "违章"],
    },
    {
        "content": "2026年4月8日预约4月21日商务车租车。",
        "kind": "episodic",
        "cues": ["2026-04-08", "商务车"],
    },
    {
        "content": "2026年4月21日取商务车。",
        "kind": "episodic",
        "cues": ["2026-04-21", "商务车"],
    },
    {
        "content": "2026年4月23日还车完成。",
        "kind": "episodic",
        "cues": ["2026-04-23", "还车"],
    },
    {
        "content": "会员优惠：会员租车9折，免费升级。",
        "kind": "semantic",
        "cues": ["会员", "优惠"],
    },
    {
        "content": "2026年6月6日收到通知：6月20日夏季租车活动。",
        "kind": "episodic",
        "cues": ["2026-06-06", "活动"],
    },
    {
        "content": "2026年6月20日活动开始。",
        "kind": "episodic",
        "cues": ["2026-06-20", "活动"],
    },
    {
        "content": "2026年8月4日预约8月17日取车。",
        "kind": "episodic",
        "cues": ["2026-08-04", "取车"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日会员卡积分到期。",
        "kind": "episodic",
        "cues": ["2026-08-10", "积分"],
    },
]


QUESTIONS = [
    {
        "dim": "首次租车",
        "q": "第一次租车是什么时候？",
        "answer": "1月7日",
        "terms": ["7"],
    },
    {
        "dim": "日租价格",
        "q": "经济型轿车日租多少钱？",
        "answer": "180元",
        "terms": ["180"],
    },
    {
        "dim": "下次取车",
        "q": "下次取车是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "租车门店几点开门？",
        "answer": "早8点",
        "terms": ["8"],
    },
    {
        "dim": "电话",
        "q": "租车门店电话多少？",
        "answer": "0898-6666-7777",
        "terms": ["7777"],
    },
    {
        "dim": "车型",
        "q": "门店有哪些车型？",
        "answer": "经济型、舒适型、SUV、商务车",
        "terms": ["商务车"],
    },
    {
        "dim": "保险说明",
        "q": "租车保险怎么算？",
        "answer": "基础保险已含，不计免赔另购",
        "terms": ["不计免赔"],
    },
    {
        "dim": "油量规则",
        "q": "租车油量怎么算？",
        "answer": "满油取车，满油还车",
        "terms": ["满油"],
    },
    {
        "dim": "违章处理",
        "q": "违章什么时候处理的？",
        "answer": "3月24日",
        "terms": ["24"],
    },
    {
        "dim": "积分到期",
        "q": "会员卡积分什么时候到期？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="汽车租赁",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="carrental_mem0db",
        out_name="carrental_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
