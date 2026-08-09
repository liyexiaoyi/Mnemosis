"""Food-delivery membership spot-check (round 324): Mnemosis vs mem0."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日开通外卖会员。",
        "kind": "episodic",
        "cues": ["2026-01-10", "会员"],
    },
    {
        "content": "2026年1月20日第一次用会员红包。",
        "kind": "episodic",
        "cues": ["2026-01-20", "红包"],
    },
    {
        "content": "2026年2月1日会员价格：15 元/月。",
        "kind": "semantic",
        "cues": ["会员", "15"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日商家券。",
        "kind": "episodic",
        "cues": ["2026-02-15", "商家券"],
    },
    {
        "content": "2026年2月25日领券完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "商家券"],
    },
    {
        "content": "2026年3月1日点外卖：满 30 减 8。",
        "kind": "episodic",
        "cues": ["2026-03-01", "满减"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日会员日。",
        "kind": "episodic",
        "cues": ["2026-03-15", "会员日"],
    },
    {
        "content": "2026年3月25日会员日半价。",
        "kind": "episodic",
        "cues": ["2026-03-25", "会员日"],
    },
    {
        "content": "2026年4月1日退款：4 月 10 日到账。",
        "kind": "episodic",
        "cues": ["2026-04-01", "退款"],
    },
    {
        "content": "2026年4月10日退款到账。",
        "kind": "episodic",
        "cues": ["2026-04-10", "退款"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日免配送费。",
        "kind": "episodic",
        "cues": ["2026-05-01", "免配送"],
    },
    {
        "content": "2026年5月15日免配送完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "免配送"],
    },
    {
        "content": "2026年6月1日会员过期：6 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-06-01", "过期"],
    },
    {
        "content": "2026年6月20日续会员。",
        "kind": "episodic",
        "cues": ["2026-06-20", "续费"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日超值套餐。",
        "kind": "episodic",
        "cues": ["2026-07-01", "套餐"],
    },
    {
        "content": "2026年7月15日套餐完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "套餐"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日会员日。",
        "kind": "episodic",
        "cues": ["2026-08-01", "会员日"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日会员续费。",
        "kind": "episodic",
        "cues": ["2026-08-05", "续费"],
    },
    {
        "content": "外卖客服 400-333-8888。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "会员规则：满 20 免配送。",
        "kind": "semantic",
        "cues": ["会员规则"],
    },
]


QUESTIONS = [
    {
        "dim": "会员价格",
        "q": "会员多少钱一个月？",
        "answer": "15元",
        "terms": ["15"],
    },
    {
        "dim": "会员红包",
        "q": "会员红包什么时候第一次用？",
        "answer": "1月20日",
        "terms": ["20"],
    },
    {
        "dim": "满减优惠",
        "q": "满多少减多少？",
        "answer": "满30减8",
        "terms": ["8"],
    },
    {
        "dim": "未来安排",
        "q": "下次会员日是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "退款记录",
        "q": "退款什么时候到账？",
        "answer": "4月10日",
        "terms": ["10"],
    },
    {
        "dim": "免配送",
        "q": "免配送什么时候？",
        "answer": "5月15日",
        "terms": ["15"],
    },
    {
        "dim": "会员续费",
        "q": "会员什么时候续的？",
        "answer": "6月20日",
        "terms": ["20"],
    },
    {
        "dim": "外卖客服",
        "q": "外卖客服电话多少？",
        "answer": "400-333-8888",
        "terms": ["8888"],
    },
    {
        "dim": "会员规则",
        "q": "满多少免配送？",
        "answer": "满20",
        "terms": ["20"],
    },
    {
        "dim": "续费提醒",
        "q": "会员什么时候续费？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="外卖会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="delivery_mem0db",
        out_name="delivery_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
