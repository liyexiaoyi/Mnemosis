"""Kids-coding-class spot-check (round 359): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月8日报名儿童编程班，一学期3600元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "报名"],
    },
    {
        "content": "2026年1月15日第一次上编程课。",
        "kind": "episodic",
        "cues": ["2026-01-15", "上课"],
    },
    {
        "content": "编程班每周日下午上课。",
        "kind": "semantic",
        "cues": ["课表", "周日"],
    },
    {
        "content": "课程内容：Scratch、Python入门、机器人搭建、作品展示。",
        "kind": "semantic",
        "cues": ["内容", "Scratch"],
    },
    {
        "content": "编程班电话 0512-6666-5555。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "2026年2月2日预约2月16日Scratch作品课。",
        "kind": "episodic",
        "cues": ["2026-02-02", "Scratch"],
    },
    {
        "content": "2026年2月16日作品课完成。",
        "kind": "episodic",
        "cues": ["2026-02-16", "Scratch"],
    },
    {
        "content": "2026年3月6日收到通知：3月20日编程比赛。",
        "kind": "episodic",
        "cues": ["2026-03-06", "比赛"],
    },
    {
        "content": "2026年3月20日比赛完成，获得二等奖。",
        "kind": "episodic",
        "cues": ["2026-03-20", "比赛"],
    },
    {
        "content": "请假补课规则：请假可安排周三补课。",
        "kind": "semantic",
        "cues": ["请假", "补课"],
    },
    {
        "content": "2026年4月10日预约4月24日Python入门课。",
        "kind": "episodic",
        "cues": ["2026-04-10", "Python"],
    },
    {
        "content": "2026年4月24日Python课完成。",
        "kind": "episodic",
        "cues": ["2026-04-24", "Python"],
    },
    {
        "content": "2026年5月8日收到通知：5月22日家长开放课。",
        "kind": "episodic",
        "cues": ["2026-05-08", "开放课"],
    },
    {
        "content": "2026年5月22日开放课完成。",
        "kind": "episodic",
        "cues": ["2026-05-22", "开放课"],
    },
    {
        "content": "2026年6月10日预约6月24日机器人搭建课。",
        "kind": "episodic",
        "cues": ["2026-06-10", "机器人"],
    },
    {
        "content": "2026年6月24日机器人课完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "机器人"],
    },
    {
        "content": "2026年7月8日收到通知：7月20日暑期集训。",
        "kind": "episodic",
        "cues": ["2026-07-08", "集训"],
    },
    {
        "content": "2026年7月20日暑期集训开始。",
        "kind": "episodic",
        "cues": ["2026-07-20", "集训"],
    },
    {
        "content": "2026年8月3日预约8月16日下次上课。",
        "kind": "episodic",
        "cues": ["2026-08-03", "上课"],
    },
    {
        "content": "2026年8月10日收到提醒：8月26日续费优惠截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "续费"],
    },
]


QUESTIONS = [
    {
        "dim": "报名时间",
        "q": "编程班第一次什么时候报名的？",
        "answer": "1月8日",
        "terms": ["8"],
    },
    {
        "dim": "学费",
        "q": "一学期学费多少钱？",
        "answer": "3600元",
        "terms": ["3600"],
    },
    {
        "dim": "下次上课",
        "q": "下次上课是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "上课时间",
        "q": "编程课每周几上？",
        "answer": "周日",
        "terms": ["周日"],
    },
    {
        "dim": "电话",
        "q": "编程班电话多少？",
        "answer": "0512-6666-5555",
        "terms": ["5555"],
    },
    {
        "dim": "课程内容",
        "q": "课程有哪些内容？",
        "answer": "Scratch、Python入门、机器人搭建、作品展示",
        "terms": ["机器人"],
    },
    {
        "dim": "比赛结果",
        "q": "编程比赛结果是什么？",
        "answer": "二等奖",
        "terms": ["二等奖"],
    },
    {
        "dim": "补课规则",
        "q": "请假怎么补课？",
        "answer": "周三补课",
        "terms": ["周三"],
    },
    {
        "dim": "暑期集训",
        "q": "暑期集训什么时候开始？",
        "answer": "7月20日",
        "terms": ["20"],
    },
    {
        "dim": "续费优惠",
        "q": "续费优惠什么时候截止？",
        "answer": "8月26日",
        "terms": ["26"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="儿童编程班",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="coding_mem0db",
        out_name="coding_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
