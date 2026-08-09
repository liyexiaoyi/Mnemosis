"""Nail-salon spot-check (round 354): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月6日第一次去美甲店，办会员卡充值500元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "会员卡"],
    },
    {
        "content": "2026年1月10日第一次做美甲，纯色套餐98元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "美甲"],
    },
    {
        "content": "美甲店营业时间：早10点到晚9点。",
        "kind": "semantic",
        "cues": ["营业时间", "10点"],
    },
    {
        "content": "美甲店电话 0551-6666-1111。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "服务项目：纯色美甲、法式、渐变、贴钻、足部护理。",
        "kind": "semantic",
        "cues": ["服务", "项目"],
    },
    {
        "content": "2026年2月3日预约2月15日法式美甲。",
        "kind": "episodic",
        "cues": ["2026-02-03", "法式"],
    },
    {
        "content": "2026年2月15日法式美甲完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "法式"],
    },
    {
        "content": "会员折扣：会员消费9折。",
        "kind": "semantic",
        "cues": ["会员", "折扣"],
    },
    {
        "content": "消毒说明：工具每次使用前高温消毒。",
        "kind": "semantic",
        "cues": ["消毒", "说明"],
    },
    {
        "content": "2026年3月10日收到通知：3月24日春季款式上新。",
        "kind": "episodic",
        "cues": ["2026-03-10", "上新"],
    },
    {
        "content": "2026年3月24日选择樱花渐变款式。",
        "kind": "episodic",
        "cues": ["2026-03-24", "渐变"],
    },
    {
        "content": "2026年4月8日预约4月22日贴钻美甲。",
        "kind": "episodic",
        "cues": ["2026-04-08", "贴钻"],
    },
    {
        "content": "2026年4月22日贴钻美甲完成。",
        "kind": "episodic",
        "cues": ["2026-04-22", "贴钻"],
    },
    {
        "content": "2026年5月10日收到通知：5月24日母亲节活动。",
        "kind": "episodic",
        "cues": ["2026-05-10", "母亲节"],
    },
    {
        "content": "2026年5月24日母亲节活动完成。",
        "kind": "episodic",
        "cues": ["2026-05-24", "母亲节"],
    },
    {
        "content": "2026年6月8日预约6月22日足部护理。",
        "kind": "episodic",
        "cues": ["2026-06-08", "足部护理"],
    },
    {
        "content": "2026年6月22日足部护理完成。",
        "kind": "episodic",
        "cues": ["2026-06-22", "足部护理"],
    },
    {
        "content": "2026年7月10日收到通知：7月26日积分双倍活动。",
        "kind": "episodic",
        "cues": ["2026-07-10", "积分"],
    },
    {
        "content": "2026年8月3日预约8月16日下次美甲。",
        "kind": "episodic",
        "cues": ["2026-08-03", "美甲"],
    },
    {
        "content": "2026年8月10日收到提醒：8月26日会员卡余额不足。",
        "kind": "episodic",
        "cues": ["2026-08-10", "余额"],
    },
]


QUESTIONS = [
    {
        "dim": "首次办卡",
        "q": "美甲店会员卡第一次什么时候办的？",
        "answer": "1月6日",
        "terms": ["6"],
    },
    {
        "dim": "套餐价格",
        "q": "纯色套餐多少钱？",
        "answer": "98元",
        "terms": ["98"],
    },
    {
        "dim": "下次美甲",
        "q": "下次美甲是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "营业时间",
        "q": "美甲店几点开门？",
        "answer": "早10点",
        "terms": ["10"],
    },
    {
        "dim": "电话",
        "q": "美甲店电话多少？",
        "answer": "0551-6666-1111",
        "terms": ["1111"],
    },
    {
        "dim": "服务项目",
        "q": "美甲店有哪些服务项目？",
        "answer": "纯色、法式、渐变、贴钻、足部护理",
        "terms": ["足部护理"],
    },
    {
        "dim": "会员折扣",
        "q": "会员消费打几折？",
        "answer": "9折",
        "terms": ["9"],
    },
    {
        "dim": "消毒说明",
        "q": "美甲工具怎么消毒？",
        "answer": "使用前高温消毒",
        "terms": ["高温"],
    },
    {
        "dim": "款式选择",
        "q": "3月选了哪个款式？",
        "answer": "樱花渐变",
        "terms": ["樱花"],
    },
    {
        "dim": "余额提醒",
        "q": "会员卡余额什么时候会不足？",
        "answer": "8月26日",
        "terms": ["26"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="美甲店",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="nail_mem0db",
        out_name="nail_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
