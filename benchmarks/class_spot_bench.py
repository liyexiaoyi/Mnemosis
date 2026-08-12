"""Children-classes spot-check (round 291): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日报画画班：每周末。",
        "kind": "semantic",
        "cues": ["画画班"],
    },
    {
        "content": "2026年1月20日报游泳班：12 节课 2400 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "游泳班"],
    },
    {
        "content": "2026年2月1日画画班开课。",
        "kind": "episodic",
        "cues": ["2026-02-01", "画画"],
    },
    {
        "content": "2026年2月15日游泳第一课。",
        "kind": "episodic",
        "cues": ["2026-02-15", "游泳"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日游泳测试。",
        "kind": "episodic",
        "cues": ["2026-03-01", "游泳"],
    },
    {
        "content": "2026年3月15日游泳测试通过。",
        "kind": "episodic",
        "cues": ["2026-03-15", "游泳"],
    },
    {
        "content": "2026年4月1日报钢琴班：一对一。",
        "kind": "semantic",
        "cues": ["钢琴班"],
    },
    {
        "content": "2026年4月15日钢琴第一课。",
        "kind": "episodic",
        "cues": ["2026-04-15", "钢琴"],
    },
    {
        "content": "2026年5月1日画画作品获奖。",
        "kind": "episodic",
        "cues": ["2026-05-01", "获奖"],
    },
    {
        "content": "2026年5月20日预约 6 月 1 日钢琴考级。",
        "kind": "episodic",
        "cues": ["2026-05-20", "考级"],
    },
    {
        "content": "2026年6月1日钢琴考级。",
        "kind": "episodic",
        "cues": ["2026-06-01", "考级"],
    },
    {
        "content": "2026年6月15日考级通过。",
        "kind": "episodic",
        "cues": ["2026-06-15", "考级"],
    },
    {
        "content": "2026年7月1日游泳班续费：2400 元。",
        "kind": "episodic",
        "cues": ["2026-07-01", "续费"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日游泳比赛。",
        "kind": "episodic",
        "cues": ["2026-07-15", "比赛"],
    },
    {
        "content": "2026年7月25日游泳比赛第二名。",
        "kind": "episodic",
        "cues": ["2026-07-25", "比赛"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日画画展。",
        "kind": "episodic",
        "cues": ["2026-08-01", "画画展"],
    },
    {
        "content": "2026年8月5日收到通知：8 月 20 日家长会。",
        "kind": "episodic",
        "cues": ["2026-08-05", "家长会"],
    },
    {
        "content": "兴趣班老师电话 139-7777-8888。",
        "kind": "semantic",
        "cues": ["老师", "电话"],
    },
    {
        "content": "画画工具：水彩笔。",
        "kind": "semantic",
        "cues": ["画画", "工具"],
    },
    {
        "content": "2026年8月8日收到提醒：8 月 15 日钢琴课调课。",
        "kind": "episodic",
        "cues": ["2026-08-08", "调课"],
    },
]


QUESTIONS = [
    {
        "dim": "报名记录",
        "q": "报了什么班？",
        "answer": "画画、游泳、钢琴",
        "terms": ["钢琴"],
    },
    {
        "dim": "课程费用",
        "q": "游泳班多少钱？",
        "answer": "2400元",
        "terms": ["2400"],
    },
    {
        "dim": "考级记录",
        "q": "钢琴考级什么时候？过了吗？",
        "answer": "6月1日，通过",
        "terms": ["通过"],
    },
    {
        "dim": "比赛记录",
        "q": "上次游泳比赛什么时候？第几名？",
        "answer": "7月25日，第二名",
        "terms": ["第二名"],
    },
    {
        "dim": "未来安排",
        "q": "下次画画展是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "家长会",
        "q": "家长会什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "获奖记录",
        "q": "画画获奖是什么时候？",
        "answer": "5月1日",
        "terms": ["1"],
    },
    {
        "dim": "老师电话",
        "q": "兴趣班老师电话多少？",
        "answer": "139-7777-8888",
        "terms": ["8888"],
    },
    {
        "dim": "调课提醒",
        "q": "钢琴课什么时候调课？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "画画工具",
        "q": "画画用什么工具？",
        "answer": "水彩笔",
        "terms": ["水彩笔"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="少儿兴趣班",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="class_mem0db",
        out_name="class_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
