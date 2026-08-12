"""Coffee-roastery spot-check (round 337): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月4日第一次在烘焙店买咖啡豆，耶加雪菲半磅88元。",
        "kind": "episodic",
        "cues": ["2026-01-04", "咖啡豆"],
    },
    {
        "content": "2026年1月10日取第一次烘焙的豆子。",
        "kind": "episodic",
        "cues": ["2026-01-10", "取豆"],
    },
    {
        "content": "烘焙店营业时间：早9点到晚8点。",
        "kind": "semantic",
        "cues": ["营业时间", "9点"],
    },
    {
        "content": "烘焙店电话 029-1234-5678。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "2026年2月6日购买哥伦比亚豆半磅96元。",
        "kind": "episodic",
        "cues": ["2026-02-06", "哥伦比亚"],
    },
    {
        "content": "2026年2月12日取哥伦比亚豆。",
        "kind": "episodic",
        "cues": ["2026-02-12", "取豆"],
    },
    {
        "content": "2026年3月8日预约3月21日曼特宁豆烘焙。",
        "kind": "episodic",
        "cues": ["2026-03-08", "曼特宁"],
    },
    {
        "content": "2026年3月21日取曼特宁豆。",
        "kind": "episodic",
        "cues": ["2026-03-21", "曼特宁"],
    },
    {
        "content": "会员积分规则：每消费10元积1分。",
        "kind": "semantic",
        "cues": ["积分", "规则"],
    },
    {
        "content": "2026年4月10日收到通知：4月25日烘焙店杯测会。",
        "kind": "episodic",
        "cues": ["2026-04-10", "杯测会"],
    },
    {
        "content": "2026年4月25日杯测会完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "杯测会"],
    },
    {
        "content": "配送规则：满200元包邮，次日达。",
        "kind": "semantic",
        "cues": ["配送", "包邮"],
    },
    {
        "content": "2026年5月6日购买咖啡豆180元，选择快递配送。",
        "kind": "episodic",
        "cues": ["2026-05-06", "快递"],
    },
    {
        "content": "2026年5月7日收到咖啡豆快递。",
        "kind": "episodic",
        "cues": ["2026-05-07", "快递"],
    },
    {
        "content": "2026年6月9日预约6月22日瑰夏豆烘焙。",
        "kind": "episodic",
        "cues": ["2026-06-09", "瑰夏"],
    },
    {
        "content": "2026年6月22日取瑰夏豆。",
        "kind": "episodic",
        "cues": ["2026-06-22", "瑰夏"],
    },
    {
        "content": "咖啡豆保质期：烘焙后45天内最佳。",
        "kind": "semantic",
        "cues": ["保质期", "45天"],
    },
    {
        "content": "2026年7月8日收到通知：7月20日烘焙体验课。",
        "kind": "episodic",
        "cues": ["2026-07-08", "体验课"],
    },
    {
        "content": "2026年7月20日体验课完成。",
        "kind": "episodic",
        "cues": ["2026-07-20", "体验课"],
    },
    {
        "content": "2026年8月4日预约8月18日下次烘焙。",
        "kind": "episodic",
        "cues": ["2026-08-04", "烘焙"],
    },
]


QUESTIONS = [
    {
        "dim": "首次购买",
        "q": "第一次在烘焙店买豆是什么时候？",
        "answer": "1月4日",
        "terms": ["4"],
    },
    {
        "dim": "豆价",
        "q": "耶加雪菲半磅多少钱？",
        "answer": "88元",
        "terms": ["88"],
    },
    {
        "dim": "下次烘焙",
        "q": "下次烘焙取豆是什么时候？",
        "answer": "8月18日",
        "terms": ["18"],
    },
    {
        "dim": "营业时间",
        "q": "烘焙店几点开门？",
        "answer": "早9点",
        "terms": ["9"],
    },
    {
        "dim": "电话",
        "q": "烘焙店电话多少？",
        "answer": "029-1234-5678",
        "terms": ["5678"],
    },
    {
        "dim": "积分规则",
        "q": "消费多少积1分？",
        "answer": "10元",
        "terms": ["10"],
    },
    {
        "dim": "杯测会",
        "q": "杯测会什么时候？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "配送规则",
        "q": "咖啡豆满多少钱包邮？",
        "answer": "200元",
        "terms": ["200"],
    },
    {
        "dim": "保质期",
        "q": "咖啡豆烘焙后多久内最佳？",
        "answer": "45天内",
        "terms": ["45"],
    },
    {
        "dim": "体验课",
        "q": "烘焙体验课什么时候上的？",
        "answer": "7月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="咖啡豆烘焙店",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="roastery_mem0db",
        out_name="roastery_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
