"""Hourly-housekeeper spot-check (round 343): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月7日第一次请钟点工，每小时60元。",
        "kind": "episodic",
        "cues": ["2026-01-07", "钟点工"],
    },
    {
        "content": "2026年1月12日第一次服务完成，打扫3小时。",
        "kind": "episodic",
        "cues": ["2026-01-12", "打扫"],
    },
    {
        "content": "服务范围：打扫、洗衣、做饭，不含擦窗。",
        "kind": "semantic",
        "cues": ["范围", "打扫"],
    },
    {
        "content": "钟点工平台电话 010-6666-8888。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "2026年2月3日预约2月16日春节前大扫除。",
        "kind": "episodic",
        "cues": ["2026-02-03", "大扫除"],
    },
    {
        "content": "2026年2月16日大扫除完成，4小时。",
        "kind": "episodic",
        "cues": ["2026-02-16", "大扫除"],
    },
    {
        "content": "请假规则：临时取消需提前3小时告知。",
        "kind": "semantic",
        "cues": ["取消", "规则"],
    },
    {
        "content": "2026年3月10日收到通知：3月24日服务人员考核。",
        "kind": "episodic",
        "cues": ["2026-03-10", "考核"],
    },
    {
        "content": "2026年3月24日考核完成，评为五星。",
        "kind": "episodic",
        "cues": ["2026-03-24", "考核"],
    },
    {
        "content": "2026年4月8日购买钟点工服务保险，年费90元。",
        "kind": "episodic",
        "cues": ["2026-04-08", "保险"],
    },
    {
        "content": "2026年4月20日收到通知：五一假期服务费上浮20%。",
        "kind": "episodic",
        "cues": ["2026-04-20", "假期"],
    },
    {
        "content": "2026年5月6日预约5月19日常规打扫。",
        "kind": "episodic",
        "cues": ["2026-05-06", "打扫"],
    },
    {
        "content": "2026年5月19日常规打扫完成。",
        "kind": "episodic",
        "cues": ["2026-05-19", "打扫"],
    },
    {
        "content": "结算方式：每次服务后线上支付。",
        "kind": "semantic",
        "cues": ["结算", "支付"],
    },
    {
        "content": "2026年6月10日收到通知：6月24日钟点工技能培训。",
        "kind": "episodic",
        "cues": ["2026-06-10", "培训"],
    },
    {
        "content": "2026年6月24日培训完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "培训"],
    },
    {
        "content": "2026年7月5日预约7月18日做饭服务。",
        "kind": "episodic",
        "cues": ["2026-07-05", "做饭"],
    },
    {
        "content": "2026年7月18日做饭服务完成。",
        "kind": "episodic",
        "cues": ["2026-07-18", "做饭"],
    },
    {
        "content": "2026年8月3日预约8月16日下次打扫。",
        "kind": "episodic",
        "cues": ["2026-08-03", "打扫"],
    },
    {
        "content": "2026年8月10日收到提醒：8月23日保险续费。",
        "kind": "episodic",
        "cues": ["2026-08-10", "保险"],
    },
]


QUESTIONS = [
    {
        "dim": "首次服务",
        "q": "第一次请钟点工是什么时候？",
        "answer": "1月7日",
        "terms": ["7"],
    },
    {
        "dim": "每小时费用",
        "q": "钟点工每小时多少钱？",
        "answer": "60元",
        "terms": ["60"],
    },
    {
        "dim": "下次服务",
        "q": "下次钟点工服务是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "服务范围",
        "q": "钟点工服务包括哪些？",
        "answer": "打扫、洗衣、做饭，不含擦窗",
        "terms": ["擦窗"],
    },
    {
        "dim": "平台电话",
        "q": "钟点工平台电话多少？",
        "answer": "010-6666-8888",
        "terms": ["8888"],
    },
    {
        "dim": "取消规则",
        "q": "临时取消要提前多久告知？",
        "answer": "提前3小时",
        "terms": ["3"],
    },
    {
        "dim": "假期费用",
        "q": "五一假期服务费上浮多少？",
        "answer": "20%",
        "terms": ["20"],
    },
    {
        "dim": "结算方式",
        "q": "钟点工服务怎么结算？",
        "answer": "线上支付",
        "terms": ["线上"],
    },
    {
        "dim": "考核",
        "q": "钟点工考核结果是什么？",
        "answer": "五星",
        "terms": ["五星"],
    },
    {
        "dim": "保险续费",
        "q": "保险什么时候续费？",
        "answer": "8月23日",
        "terms": ["23"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="钟点工服务",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="cleaner_mem0db",
        out_name="cleaner_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
