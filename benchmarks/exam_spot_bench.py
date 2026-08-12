"""Bar-exam prep spot-check (round 278): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月5日报名法考：3 月 15 日缴费截止。",
        "kind": "episodic",
        "cues": ["2026-01-05", "法考"],
    },
    {
        "content": "2026年1月15日买教材：民法、刑法、民诉。",
        "kind": "semantic",
        "cues": ["教材", "民法"],
    },
    {
        "content": "2026年2月1日开始每天学习 2 小时。",
        "kind": "episodic",
        "cues": ["2026-02-01", "学习"],
    },
    {
        "content": "2026年2月15日第一轮复习民法完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "民法"],
    },
    {
        "content": "2026年3月1日模考一：58 分。",
        "kind": "episodic",
        "cues": ["2026-03-01", "模考"],
    },
    {
        "content": "2026年3月15日缴费成功。",
        "kind": "episodic",
        "cues": ["2026-03-15", "缴费"],
    },
    {
        "content": "2026年3月25日第二轮刑法完成。",
        "kind": "episodic",
        "cues": ["2026-03-25", "刑法"],
    },
    {
        "content": "2026年4月5日模考二：66 分。",
        "kind": "episodic",
        "cues": ["2026-04-05", "模考"],
    },
    {
        "content": "2026年4月20日报线下冲刺班：5 月 1 日开课。",
        "kind": "episodic",
        "cues": ["2026-04-20", "冲刺班"],
    },
    {
        "content": "2026年5月1日冲刺班开课。",
        "kind": "episodic",
        "cues": ["2026-05-01", "冲刺班"],
    },
    {
        "content": "2026年5月15日模考三：74 分。",
        "kind": "episodic",
        "cues": ["2026-05-15", "模考"],
    },
    {
        "content": "2026年6月1日打印准考证：6 月 10 日可打印。",
        "kind": "episodic",
        "cues": ["2026-06-01", "准考证"],
    },
    {
        "content": "2026年6月10日打印准考证。",
        "kind": "episodic",
        "cues": ["2026-06-10", "准考证"],
    },
    {
        "content": "2026年6月15日客观题考试：6 月 18 日出分。",
        "kind": "episodic",
        "cues": ["2026-06-15", "客观题"],
    },
    {
        "content": "2026年6月18日客观题 182 分通过。",
        "kind": "episodic",
        "cues": ["2026-06-18", "客观题"],
    },
    {
        "content": "2026年7月1日主观题备考：每天真题 1 套。",
        "kind": "semantic",
        "cues": ["主观题", "真题"],
    },
    {
        "content": "2026年7月15日主观题模考：98 分。",
        "kind": "episodic",
        "cues": ["2026-07-15", "主观题"],
    },
    {
        "content": "2026年7月25日预约 8 月 5 日主观题考试。",
        "kind": "episodic",
        "cues": ["2026-07-25", "主观题"],
    },
    {
        "content": "2026年8月5日主观题考试。",
        "kind": "episodic",
        "cues": ["2026-08-05", "主观题"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日成绩公布。",
        "kind": "episodic",
        "cues": ["2026-08-08", "成绩"],
    },
    {
        "content": "学习地点：图书馆 3 楼自习室。",
        "kind": "semantic",
        "cues": ["图书馆", "自习室"],
    },
    {
        "content": "资料：错题本放书包。",
        "kind": "semantic",
        "cues": ["错题本", "书包"],
    },
    {
        "content": "番茄钟：学习 25 分钟休息 5 分钟。",
        "kind": "semantic",
        "cues": ["番茄钟"],
    },
    {
        "content": "2026年8月9日预约 8 月 15 日查分提醒。",
        "kind": "episodic",
        "cues": ["2026-08-09", "查分"],
    },
]


QUESTIONS = [
    {
        "dim": "报名缴费",
        "q": "法考什么时候缴费截止？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "教材清单",
        "q": "买了哪些教材？",
        "answer": "民法、刑法、民诉",
        "terms": ["民法"],
    },
    {
        "dim": "模考成绩",
        "q": "最近一次客观题模考多少分？",
        "answer": "74分",
        "terms": ["74"],
    },
    {
        "dim": "考试成绩",
        "q": "客观题考了多少分？过了吗？",
        "answer": "182分，通过",
        "terms": ["182"],
    },
    {
        "dim": "成绩公布",
        "q": "成绩什么时候公布？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "备考计划",
        "q": "现在怎么复习？",
        "answer": "每天真题1套",
        "terms": ["真题"],
    },
    {
        "dim": "冲刺班",
        "q": "冲刺班什么时候开课？",
        "answer": "5月1日",
        "terms": ["1"],
    },
    {
        "dim": "学习地点",
        "q": "在哪学习？",
        "answer": "图书馆3楼自习室",
        "terms": ["图书馆"],
    },
    {
        "dim": "学习方法",
        "q": "番茄钟怎么用？",
        "answer": "学习25分钟休息5分钟",
        "terms": ["25"],
    },
    {
        "dim": "资料存放",
        "q": "错题本放哪？",
        "answer": "书包",
        "terms": ["书包"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="法考备考",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="exam_mem0db",
        out_name="exam_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
