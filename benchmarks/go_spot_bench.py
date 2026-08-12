"""Kids-Go-class spot-check (round 331): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月12日报名儿童围棋班，每期2000元。",
        "kind": "episodic",
        "cues": ["2026-01-12", "围棋班"],
    },
    {
        "content": "2026年1月20日第一次上围棋课。",
        "kind": "episodic",
        "cues": ["2026-01-20", "围棋"],
    },
    {
        "content": "围棋班每周六上课。",
        "kind": "semantic",
        "cues": ["课表", "周六"],
    },
    {
        "content": "2026年2月15日购买围棋教材：《围棋入门》和棋盘。",
        "kind": "episodic",
        "cues": ["2026-02-15", "教材"],
    },
    {
        "content": "2026年3月1日收到通知：3月15日围棋班内部比赛。",
        "kind": "episodic",
        "cues": ["2026-03-01", "比赛"],
    },
    {
        "content": "2026年3月15日内部比赛完成，孩子获得第三名。",
        "kind": "episodic",
        "cues": ["2026-03-15", "比赛"],
    },
    {
        "content": "2026年4月2日预约4月20日围棋考级。",
        "kind": "episodic",
        "cues": ["2026-04-02", "考级"],
    },
    {
        "content": "2026年4月20日围棋考级通过，定为8级。",
        "kind": "episodic",
        "cues": ["2026-04-20", "考级"],
    },
    {
        "content": "围棋老师电话 138-0000-8888。",
        "kind": "semantic",
        "cues": ["老师", "电话"],
    },
    {
        "content": "请假规则：提前一天在群里请假。",
        "kind": "semantic",
        "cues": ["请假", "规则"],
    },
    {
        "content": "2026年6月5日预约6月30日家长会。",
        "kind": "episodic",
        "cues": ["2026-06-05", "家长会"],
    },
    {
        "content": "2026年6月30日家长会完成，老师建议每天练棋30分钟。",
        "kind": "episodic",
        "cues": ["2026-06-30", "家长会"],
    },
    {
        "content": "2026年6月10日补交教材费：120元。",
        "kind": "episodic",
        "cues": ["2026-06-10", "教材费"],
    },
    {
        "content": "2026年7月3日孩子请假一次，改为周五补课。",
        "kind": "episodic",
        "cues": ["2026-07-03", "请假"],
    },
    {
        "content": "2026年7月8日收到通知：7月25日围棋夏令营。",
        "kind": "episodic",
        "cues": ["2026-07-08", "夏令营"],
    },
    {
        "content": "2026年7月25日夏令营开始，为期一周。",
        "kind": "episodic",
        "cues": ["2026-07-25", "夏令营"],
    },
    {
        "content": "2026年8月1日预约8月16日下一期报名续费。",
        "kind": "episodic",
        "cues": ["2026-08-01", "续费"],
    },
    {
        "content": "2026年8月12日老师通知：8月22日周六围棋课正常上课。",
        "kind": "episodic",
        "cues": ["2026-08-12", "上课"],
    },
    {
        "content": "2026年8月15日收到提醒：8月30日围棋公开赛报名截止。",
        "kind": "episodic",
        "cues": ["2026-08-15", "公开赛"],
    },
    {
        "content": "2026年8月18日老师通知：9月6日参加市级围棋比赛。",
        "kind": "episodic",
        "cues": ["2026-08-18", "市级比赛"],
    },
    {
        "content": "围棋课每次两小时，含休息10分钟。",
        "kind": "semantic",
        "cues": ["课时", "两小时"],
    },
]


QUESTIONS = [
    {
        "dim": "报名时间",
        "q": "围棋班第一次报名是什么时候？",
        "answer": "1月12日",
        "terms": ["1"],
    },
    {
        "dim": "课程费用",
        "q": "围棋班一期多少钱？",
        "answer": "2000元",
        "terms": ["2000"],
    },
    {
        "dim": "下次上课",
        "q": "下次围棋课是什么时候？",
        "answer": "8月22日",
        "terms": ["22"],
    },
    {
        "dim": "上课时间",
        "q": "围棋课每周几上？",
        "answer": "周六",
        "terms": ["周六"],
    },
    {
        "dim": "考级结果",
        "q": "围棋考级过了吗？现在什么级别？",
        "answer": "通过，8级",
        "terms": ["8"],
    },
    {
        "dim": "老师电话",
        "q": "围棋老师电话多少？",
        "answer": "138-0000-8888",
        "terms": ["8888"],
    },
    {
        "dim": "请假流程",
        "q": "孩子上课请假怎么处理？",
        "answer": "提前一天在群里请假",
        "terms": ["群"],
    },
    {
        "dim": "比赛安排",
        "q": "市级围棋比赛什么时候？",
        "answer": "9月6日",
        "terms": ["6"],
    },
    {
        "dim": "家长会",
        "q": "家长会什么时候开的？",
        "answer": "6月30日",
        "terms": ["30"],
    },
    {
        "dim": "夏令营",
        "q": "围棋夏令营什么时候开始？",
        "answer": "7月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="儿童围棋班",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="go_mem0db",
        out_name="go_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
