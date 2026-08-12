"""Swimming-pool-membership spot-check (round 333): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月6日办理游泳馆年卡，费用3600元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "年卡"],
    },
    {
        "content": "2026年1月13日第一次去游泳馆游泳。",
        "kind": "episodic",
        "cues": ["2026-01-13", "游泳"],
    },
    {
        "content": "游泳馆营业时间：早6点到晚10点。",
        "kind": "semantic",
        "cues": ["营业时间", "6点"],
    },
    {
        "content": "2026年2月1日预约2月14日私教课。",
        "kind": "episodic",
        "cues": ["2026-02-01", "私教课"],
    },
    {
        "content": "2026年2月14日第一节私教课完成。",
        "kind": "episodic",
        "cues": ["2026-02-14", "私教课"],
    },
    {
        "content": "2026年2月20日购买泳镜和泳帽。",
        "kind": "episodic",
        "cues": ["2026-02-20", "购买"],
    },
    {
        "content": "游泳馆前台电话 010-8888-1234。",
        "kind": "semantic",
        "cues": ["前台", "电话"],
    },
    {
        "content": "停卡规则：出差可申请停卡，每月最多一次。",
        "kind": "semantic",
        "cues": ["停卡", "规则"],
    },
    {
        "content": "2026年3月10日申请停卡两周。",
        "kind": "episodic",
        "cues": ["2026-03-10", "停卡"],
    },
    {
        "content": "2026年3月28日恢复游泳。",
        "kind": "episodic",
        "cues": ["2026-03-28", "恢复"],
    },
    {
        "content": "2026年4月5日收到通知：4月20日游泳馆会员赛。",
        "kind": "episodic",
        "cues": ["2026-04-05", "会员赛"],
    },
    {
        "content": "2026年4月20日会员赛完成，获得蛙泳组第三名。",
        "kind": "episodic",
        "cues": ["2026-04-20", "会员赛"],
    },
    {
        "content": "2026年5月7日办理游泳健康证。",
        "kind": "episodic",
        "cues": ["2026-05-07", "健康证"],
    },
    {
        "content": "2026年5月18日预约6月1日自由泳私教课。",
        "kind": "episodic",
        "cues": ["2026-05-18", "私教课"],
    },
    {
        "content": "2026年6月1日自由泳私教课完成。",
        "kind": "episodic",
        "cues": ["2026-06-01", "私教课"],
    },
    {
        "content": "2026年6月20日续买游泳月卡，费用400元。",
        "kind": "episodic",
        "cues": ["2026-06-20", "月卡"],
    },
    {
        "content": "2026年7月10日收到通知：7月26日水上安全讲座。",
        "kind": "episodic",
        "cues": ["2026-07-10", "讲座"],
    },
    {
        "content": "2026年7月26日讲座完成。",
        "kind": "episodic",
        "cues": ["2026-07-26", "讲座"],
    },
    {
        "content": "2026年8月2日预约8月15日游泳馆闭馆维护后开放。",
        "kind": "episodic",
        "cues": ["2026-08-02", "维护"],
    },
    {
        "content": "2026年8月10日收到提醒：8月23日年卡续费优惠截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "续费"],
    },
]


QUESTIONS = [
    {
        "dim": "年卡办理",
        "q": "游泳年卡第一次什么时候办的？",
        "answer": "1月6日",
        "terms": ["6"],
    },
    {
        "dim": "年卡费用",
        "q": "游泳年卡多少钱？",
        "answer": "3600元",
        "terms": ["3600"],
    },
    {
        "dim": "下次开放",
        "q": "游泳馆下次什么时候开放？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "营业时间",
        "q": "游泳馆几点开门？",
        "answer": "早6点",
        "terms": ["6"],
    },
    {
        "dim": "私教课",
        "q": "自由泳私教课什么时候上的？",
        "answer": "6月1日",
        "terms": ["1"],
    },
    {
        "dim": "前台电话",
        "q": "游泳馆前台电话多少？",
        "answer": "010-8888-1234",
        "terms": ["1234"],
    },
    {
        "dim": "停卡规则",
        "q": "什么情况下可以申请停卡？",
        "answer": "出差可申请，每月最多一次",
        "terms": ["出差"],
    },
    {
        "dim": "会员赛",
        "q": "游泳馆会员赛什么时候？",
        "answer": "4月20日",
        "terms": ["20"],
    },
    {
        "dim": "续费优惠",
        "q": "年卡续费优惠什么时候截止？",
        "answer": "8月23日",
        "terms": ["23"],
    },
    {
        "dim": "健康证",
        "q": "游泳健康证什么时候办的？",
        "answer": "5月7日",
        "terms": ["7"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="游泳馆会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="swim_mem0db",
        out_name="swim_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
