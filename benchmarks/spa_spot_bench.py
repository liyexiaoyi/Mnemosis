"""Hot-spring-club spot-check (round 344): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月5日第一次去温泉会所，门票168元。",
        "kind": "episodic",
        "cues": ["2026-01-05", "温泉"],
    },
    {
        "content": "2026年1月5日办理温泉会员卡，充值2000元。",
        "kind": "episodic",
        "cues": ["2026-01-05", "会员卡"],
    },
    {
        "content": "会所营业时间：早10点到晚11点。",
        "kind": "semantic",
        "cues": ["营业时间", "10点"],
    },
    {
        "content": "会所电话 027-7777-2222。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "设施项目：温泉池、汗蒸、按摩、自助餐。",
        "kind": "semantic",
        "cues": ["设施", "项目"],
    },
    {
        "content": "2026年2月6日预约2月18日温泉+自助餐套餐。",
        "kind": "episodic",
        "cues": ["2026-02-06", "套餐"],
    },
    {
        "content": "2026年2月18日套餐体验完成。",
        "kind": "episodic",
        "cues": ["2026-02-18", "套餐"],
    },
    {
        "content": "储物柜规则：押金50元，离店退还。",
        "kind": "semantic",
        "cues": ["储物柜", "押金"],
    },
    {
        "content": "2026年3月12日收到通知：3月26日会员日优惠。",
        "kind": "episodic",
        "cues": ["2026-03-12", "会员日"],
    },
    {
        "content": "2026年3月26日会员日消费，享受8折。",
        "kind": "episodic",
        "cues": ["2026-03-26", "会员日"],
    },
    {
        "content": "健康要求：高血压、心脏病患者不建议泡高温池。",
        "kind": "semantic",
        "cues": ["健康", "要求"],
    },
    {
        "content": "停车安排：会员免费停车3小时。",
        "kind": "semantic",
        "cues": ["停车", "免费"],
    },
    {
        "content": "2026年4月10日预约4月23日汗蒸服务。",
        "kind": "episodic",
        "cues": ["2026-04-10", "汗蒸"],
    },
    {
        "content": "2026年4月23日汗蒸完成。",
        "kind": "episodic",
        "cues": ["2026-04-23", "汗蒸"],
    },
    {
        "content": "2026年5月8日收到通知：5月22日温泉节活动。",
        "kind": "episodic",
        "cues": ["2026-05-08", "温泉节"],
    },
    {
        "content": "2026年5月22日温泉节活动完成。",
        "kind": "episodic",
        "cues": ["2026-05-22", "温泉节"],
    },
    {
        "content": "2026年6月15日预约6月28日按摩服务。",
        "kind": "episodic",
        "cues": ["2026-06-15", "按摩"],
    },
    {
        "content": "2026年6月28日按摩完成。",
        "kind": "episodic",
        "cues": ["2026-06-28", "按摩"],
    },
    {
        "content": "2026年8月2日预约8月15日下次到店。",
        "kind": "episodic",
        "cues": ["2026-08-02", "到店"],
    },
    {
        "content": "2026年8月10日收到提醒：8月24日会员卡余额不足。",
        "kind": "episodic",
        "cues": ["2026-08-10", "余额"],
    },
]


QUESTIONS = [
    {
        "dim": "首次到店",
        "q": "第一次去温泉会所是什么时候？",
        "answer": "1月5日",
        "terms": ["5"],
    },
    {
        "dim": "门票价格",
        "q": "温泉门票多少钱？",
        "answer": "168元",
        "terms": ["168"],
    },
    {
        "dim": "下次到店",
        "q": "下次到店是什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "营业时间",
        "q": "会所几点关门？",
        "answer": "晚11点",
        "terms": ["11"],
    },
    {
        "dim": "会所电话",
        "q": "温泉会所电话多少？",
        "answer": "027-7777-2222",
        "terms": ["2222"],
    },
    {
        "dim": "设施项目",
        "q": "会所有哪些设施项目？",
        "answer": "温泉池、汗蒸、按摩、自助餐",
        "terms": ["汗蒸"],
    },
    {
        "dim": "储物柜押金",
        "q": "储物柜押金多少？",
        "answer": "50元",
        "terms": ["50"],
    },
    {
        "dim": "会员停车",
        "q": "会员可以免费停车多久？",
        "answer": "3小时",
        "terms": ["3"],
    },
    {
        "dim": "健康要求",
        "q": "哪些人不建议泡高温池？",
        "answer": "高血压、心脏病患者",
        "terms": ["高血压"],
    },
    {
        "dim": "余额提醒",
        "q": "会员卡余额什么时候会不足？",
        "answer": "8月24日",
        "terms": ["24"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="温泉会所",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="spa_mem0db",
        out_name="spa_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
