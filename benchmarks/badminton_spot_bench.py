"""Badminton-hall spot-check (round 334): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月5日办理羽毛球馆年卡，费用2800元。",
        "kind": "episodic",
        "cues": ["2026-01-05", "年卡"],
    },
    {
        "content": "2026年1月12日第一次去球馆打球。",
        "kind": "episodic",
        "cues": ["2026-01-12", "打球"],
    },
    {
        "content": "球馆营业时间：早8点到晚11点。",
        "kind": "semantic",
        "cues": ["营业时间", "8点"],
    },
    {
        "content": "2026年2月3日预约2月15日晚上8点场地。",
        "kind": "episodic",
        "cues": ["2026-02-03", "场地"],
    },
    {
        "content": "2026年2月15日打球完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "打球"],
    },
    {
        "content": "2026年2月25日购买羽毛球拍和羽毛球。",
        "kind": "episodic",
        "cues": ["2026-02-25", "购买"],
    },
    {
        "content": "球馆前台电话 0755-6666-8888。",
        "kind": "semantic",
        "cues": ["前台", "电话"],
    },
    {
        "content": "场地取消规则：提前2小时可免费取消。",
        "kind": "semantic",
        "cues": ["取消", "规则"],
    },
    {
        "content": "2026年3月6日预约3月20日教练课。",
        "kind": "episodic",
        "cues": ["2026-03-06", "教练课"],
    },
    {
        "content": "2026年3月20日教练课完成。",
        "kind": "episodic",
        "cues": ["2026-03-20", "教练课"],
    },
    {
        "content": "2026年4月8日收到通知：4月25日球馆双打比赛。",
        "kind": "episodic",
        "cues": ["2026-04-08", "双打"],
    },
    {
        "content": "2026年4月25日双打比赛完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "双打"],
    },
    {
        "content": "2026年5月9日充值会员卡500元。",
        "kind": "episodic",
        "cues": ["2026-05-09", "充值"],
    },
    {
        "content": "2026年5月22日收到优惠券：6月1日前订场8折。",
        "kind": "episodic",
        "cues": ["2026-05-22", "优惠券"],
    },
    {
        "content": "2026年6月3日预约6月15日早晨场地。",
        "kind": "episodic",
        "cues": ["2026-06-03", "场地"],
    },
    {
        "content": "2026年6月15日早晨打球完成。",
        "kind": "episodic",
        "cues": ["2026-06-15", "打球"],
    },
    {
        "content": "2026年7月2日收到通知：7月18日球馆亲子活动。",
        "kind": "episodic",
        "cues": ["2026-07-02", "亲子"],
    },
    {
        "content": "2026年7月18日亲子活动完成。",
        "kind": "episodic",
        "cues": ["2026-07-18", "亲子"],
    },
    {
        "content": "2026年8月1日预约8月14日晚上场地。",
        "kind": "episodic",
        "cues": ["2026-08-01", "场地"],
    },
    {
        "content": "2026年8月10日收到提醒：8月22日年卡续费优惠截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "续费"],
    },
]


QUESTIONS = [
    {
        "dim": "年卡办理",
        "q": "羽毛球年卡第一次什么时候办的？",
        "answer": "1月5日",
        "terms": ["5"],
    },
    {
        "dim": "年卡费用",
        "q": "羽毛球年卡多少钱？",
        "answer": "2800元",
        "terms": ["2800"],
    },
    {
        "dim": "下次场地",
        "q": "下次预约的场地是什么时候？",
        "answer": "8月14日",
        "terms": ["14"],
    },
    {
        "dim": "营业时间",
        "q": "球馆几点关门？",
        "answer": "晚11点",
        "terms": ["11"],
    },
    {
        "dim": "教练课",
        "q": "教练课什么时候上的？",
        "answer": "3月20日",
        "terms": ["20"],
    },
    {
        "dim": "前台电话",
        "q": "球馆前台电话多少？",
        "answer": "0755-6666-8888",
        "terms": ["8888"],
    },
    {
        "dim": "取消规则",
        "q": "场地提前多久可以免费取消？",
        "answer": "提前2小时",
        "terms": ["2小时"],
    },
    {
        "dim": "双打比赛",
        "q": "球馆双打比赛什么时候？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "续费优惠",
        "q": "年卡续费优惠什么时候截止？",
        "answer": "8月22日",
        "terms": ["22"],
    },
    {
        "dim": "优惠券",
        "q": "订场8折优惠什么时候截止？",
        "answer": "6月1日前",
        "terms": ["1"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="羽毛球馆会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="badminton_mem0db",
        out_name="badminton_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
