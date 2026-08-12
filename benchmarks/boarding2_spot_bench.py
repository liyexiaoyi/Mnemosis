"""Pet-boarding spot-check (round 336): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月9日第一次把猫咪送去寄养，每天80元。",
        "kind": "episodic",
        "cues": ["2026-01-09", "寄养"],
    },
    {
        "content": "2026年1月15日接猫咪回家。",
        "kind": "episodic",
        "cues": ["2026-01-15", "接回"],
    },
    {
        "content": "寄养中心设施：独立猫舍、空调、监控。",
        "kind": "semantic",
        "cues": ["设施", "猫舍"],
    },
    {
        "content": "寄养中心电话 021-5555-9999。",
        "kind": "semantic",
        "cues": ["电话", "寄养"],
    },
    {
        "content": "预订规则：节假日需提前一周预订。",
        "kind": "semantic",
        "cues": ["预订", "规则"],
    },
    {
        "content": "2026年2月2日预约2月15日春节寄养。",
        "kind": "episodic",
        "cues": ["2026-02-02", "春节"],
    },
    {
        "content": "2026年2月15日送去寄养，自带猫粮。",
        "kind": "episodic",
        "cues": ["2026-02-15", "寄养"],
    },
    {
        "content": "2026年2月22日接回猫咪，并加做洗澡服务80元。",
        "kind": "episodic",
        "cues": ["2026-02-22", "洗澡"],
    },
    {
        "content": "寄养要求：需提供疫苗本和健康检查报告。",
        "kind": "semantic",
        "cues": ["疫苗本", "健康检查"],
    },
    {
        "content": "2026年3月10日带猫咪做寄养前健康检查。",
        "kind": "episodic",
        "cues": ["2026-03-10", "健康检查"],
    },
    {
        "content": "2026年4月5日预约4月18日周末寄养。",
        "kind": "episodic",
        "cues": ["2026-04-05", "周末寄养"],
    },
    {
        "content": "2026年4月18日送去寄养。",
        "kind": "episodic",
        "cues": ["2026-04-18", "寄养"],
    },
    {
        "content": "2026年4月19日接回猫咪。",
        "kind": "episodic",
        "cues": ["2026-04-19", "接回"],
    },
    {
        "content": "退款规则：预订后24小时内取消可全额退款。",
        "kind": "semantic",
        "cues": ["退款", "规则"],
    },
    {
        "content": "2026年5月10日预约5月25日寄养并支付定金200元。",
        "kind": "episodic",
        "cues": ["2026-05-10", "定金"],
    },
    {
        "content": "2026年5月20日取消5月25日寄养，获得全额退款。",
        "kind": "episodic",
        "cues": ["2026-05-20", "取消"],
    },
    {
        "content": "2026年6月8日收到通知：7月1日起寄养涨价10元每天。",
        "kind": "episodic",
        "cues": ["2026-06-08", "涨价"],
    },
    {
        "content": "2026年7月1日寄养涨价，每天90元。",
        "kind": "episodic",
        "cues": ["2026-07-01", "涨价"],
    },
    {
        "content": "2026年7月2日预约7月15日寄养。",
        "kind": "episodic",
        "cues": ["2026-07-02", "寄养"],
    },
    {
        "content": "2026年8月3日预约8月16日寄养。",
        "kind": "episodic",
        "cues": ["2026-08-03", "寄养"],
    },
    {
        "content": "2026年8月10日收到提醒：8月20日猫咪疫苗到期。",
        "kind": "episodic",
        "cues": ["2026-08-10", "疫苗"],
    },
]


QUESTIONS = [
    {
        "dim": "首次寄养",
        "q": "猫咪第一次寄养是什么时候？",
        "answer": "1月9日",
        "terms": ["9"],
    },
    {
        "dim": "寄养费用",
        "q": "猫咪第一次寄养一天多少钱？",
        "answer": "80元",
        "terms": ["80"],
    },
    {
        "dim": "下次寄养",
        "q": "下次寄养是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "寄养设施",
        "q": "寄养中心有什么设施？",
        "answer": "独立猫舍、空调、监控",
        "terms": ["猫舍"],
    },
    {
        "dim": "联系电话",
        "q": "寄养中心电话多少？",
        "answer": "021-5555-9999",
        "terms": ["9999"],
    },
    {
        "dim": "预订规则",
        "q": "节假日预订寄养要提前多久？",
        "answer": "提前一周",
        "terms": ["一周"],
    },
    {
        "dim": "健康要求",
        "q": "寄养需要带什么资料？",
        "answer": "疫苗本和健康检查报告",
        "terms": ["疫苗本"],
    },
    {
        "dim": "退款规则",
        "q": "预订后多久取消可以全额退款？",
        "answer": "24小时内",
        "terms": ["24小时"],
    },
    {
        "dim": "疫苗到期",
        "q": "猫咪疫苗什么时候到期？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "涨价通知",
        "q": "寄养什么时候涨价的？",
        "answer": "7月1日",
        "terms": ["1"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="宠物寄养",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="boarding2_mem0db",
        out_name="boarding2_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
