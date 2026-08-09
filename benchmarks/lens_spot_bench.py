"""Contact-lens-shop spot-check (round 353): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月7日第一次验配隐形眼镜，年抛套餐399元。",
        "kind": "episodic",
        "cues": ["2026-01-07", "验配"],
    },
    {
        "content": "2026年1月14日取第一副隐形眼镜。",
        "kind": "episodic",
        "cues": ["2026-01-14", "取镜"],
    },
    {
        "content": "眼镜店营业时间：早9点到晚9点半。",
        "kind": "semantic",
        "cues": ["营业时间", "9点"],
    },
    {
        "content": "眼镜店电话 0431-7777-8888。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "镜片种类：日抛、月抛、半年抛、年抛。",
        "kind": "semantic",
        "cues": ["镜片", "种类"],
    },
    {
        "content": "2026年2月2日预约2月16日复查。",
        "kind": "episodic",
        "cues": ["2026-02-02", "复查"],
    },
    {
        "content": "2026年2月16日复查完成。",
        "kind": "episodic",
        "cues": ["2026-02-16", "复查"],
    },
    {
        "content": "2026年3月8日购买护理液两瓶，共120元。",
        "kind": "episodic",
        "cues": ["2026-03-08", "护理液"],
    },
    {
        "content": "更换周期说明：月抛镜片每月更换。",
        "kind": "semantic",
        "cues": ["更换", "周期"],
    },
    {
        "content": "2026年4月10日收到通知：4月24日会员积分翻倍。",
        "kind": "episodic",
        "cues": ["2026-04-10", "积分"],
    },
    {
        "content": "2026年4月24日积分活动完成。",
        "kind": "episodic",
        "cues": ["2026-04-24", "积分"],
    },
    {
        "content": "2026年5月6日收到通知：5月20日干眼检测。",
        "kind": "episodic",
        "cues": ["2026-05-06", "干眼"],
    },
    {
        "content": "2026年5月20日干眼检测完成。",
        "kind": "episodic",
        "cues": ["2026-05-20", "干眼"],
    },
    {
        "content": "2026年6月8日预约6月22日复查。",
        "kind": "episodic",
        "cues": ["2026-06-08", "复查"],
    },
    {
        "content": "2026年6月22日复查完成。",
        "kind": "episodic",
        "cues": ["2026-06-22", "复查"],
    },
    {
        "content": "2026年7月10日收到通知：7月26日暑期套餐优惠。",
        "kind": "episodic",
        "cues": ["2026-07-10", "优惠"],
    },
    {
        "content": "2026年7月26日暑期套餐优惠开始。",
        "kind": "episodic",
        "cues": ["2026-07-26", "优惠"],
    },
    {
        "content": "2026年8月4日预约8月17日复查。",
        "kind": "episodic",
        "cues": ["2026-08-04", "复查"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日护理液促销截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "促销"],
    },
    {
        "content": "佩戴说明：初次佩戴每天不超过4小时。",
        "kind": "semantic",
        "cues": ["佩戴", "4小时"],
    },
]


QUESTIONS = [
    {
        "dim": "首次验配",
        "q": "第一次验配隐形眼镜是什么时候？",
        "answer": "1月7日",
        "terms": ["7"],
    },
    {
        "dim": "套餐费用",
        "q": "年抛套餐多少钱？",
        "answer": "399元",
        "terms": ["399"],
    },
    {
        "dim": "下次复查",
        "q": "下次复查是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "眼镜店几点关门？",
        "answer": "晚9点半",
        "terms": ["9点半"],
    },
    {
        "dim": "电话",
        "q": "眼镜店电话多少？",
        "answer": "0431-7777-8888",
        "terms": ["8888"],
    },
    {
        "dim": "镜片种类",
        "q": "店里有哪几种镜片？",
        "answer": "日抛、月抛、半年抛、年抛",
        "terms": ["日抛"],
    },
    {
        "dim": "护理液价格",
        "q": "护理液两瓶多少钱？",
        "answer": "120元",
        "terms": ["120"],
    },
    {
        "dim": "更换周期",
        "q": "月抛镜片多久更换？",
        "answer": "每月",
        "terms": ["每月"],
    },
    {
        "dim": "佩戴时长",
        "q": "初次佩戴每天不超过几小时？",
        "answer": "4小时",
        "terms": ["4"],
    },
    {
        "dim": "促销截止",
        "q": "护理液促销什么时候截止？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="隐形眼镜店",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="lens_mem0db",
        out_name="lens_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
