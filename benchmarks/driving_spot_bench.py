"""Driving-school spot-check (round 286): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日报名驾校：C1 手动挡，4600 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "驾校"],
    },
    {
        "content": "2026年1月20日科目一刷题。",
        "kind": "episodic",
        "cues": ["2026-01-20", "科目一"],
    },
    {
        "content": "2026年2月1日科目一考试：96 分通过。",
        "kind": "episodic",
        "cues": ["2026-02-01", "科目一"],
    },
    {
        "content": "2026年2月15日科目二练车开始。",
        "kind": "episodic",
        "cues": ["2026-02-15", "科目二"],
    },
    {
        "content": "2026年3月1日科目二预约：3 月 15 日考试。",
        "kind": "episodic",
        "cues": ["2026-03-01", "科目二"],
    },
    {
        "content": "2026年3月15日科目二：倒库压线，挂了。",
        "kind": "episodic",
        "cues": ["2026-03-15", "科目二"],
    },
    {
        "content": "2026年3月25日补考预约：4 月 5 日。",
        "kind": "episodic",
        "cues": ["2026-03-25", "补考"],
    },
    {
        "content": "2026年4月5日科目二补考：90 分通过。",
        "kind": "episodic",
        "cues": ["2026-04-05", "科目二"],
    },
    {
        "content": "2026年4月20日科目三练车。",
        "kind": "episodic",
        "cues": ["2026-04-20", "科目三"],
    },
    {
        "content": "2026年5月1日科目三预约：5 月 15 日。",
        "kind": "episodic",
        "cues": ["2026-05-01", "科目三"],
    },
    {
        "content": "2026年5月15日科目三：100 分通过。",
        "kind": "episodic",
        "cues": ["2026-05-15", "科目三"],
    },
    {
        "content": "2026年6月1日科目四刷题。",
        "kind": "episodic",
        "cues": ["2026-06-01", "科目四"],
    },
    {
        "content": "2026年6月10日科目四：98 分通过。",
        "kind": "episodic",
        "cues": ["2026-06-10", "科目四"],
    },
    {
        "content": "2026年6月20日拿到驾照。",
        "kind": "episodic",
        "cues": ["2026-06-20", "驾照"],
    },
    {
        "content": "2026年7月1日教练推荐新车手练车场。",
        "kind": "episodic",
        "cues": ["2026-07-01", "教练"],
    },
    {
        "content": "2026年7月10日预约 7 月 20 日陪练。",
        "kind": "episodic",
        "cues": ["2026-07-10", "陪练"],
    },
    {
        "content": "2026年7月20日第一次上路陪练。",
        "kind": "episodic",
        "cues": ["2026-07-20", "陪练"],
    },
    {
        "content": "2026年8月1日预约 8 月 10 日第二次陪练。",
        "kind": "episodic",
        "cues": ["2026-08-01", "陪练"],
    },
    {
        "content": "驾校地址：城北训练场。",
        "kind": "semantic",
        "cues": ["驾校", "城北"],
    },
    {
        "content": "教练电话 138-2222-3333。",
        "kind": "semantic",
        "cues": ["教练", "电话"],
    },
    {
        "content": "考试规则：科目一 90 分及格。",
        "kind": "semantic",
        "cues": ["考试规则"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日驾照换证体检。",
        "kind": "episodic",
        "cues": ["2026-08-05", "换证"],
    },
]


QUESTIONS = [
    {
        "dim": "报名信息",
        "q": "学车多少钱？什么车型？",
        "answer": "4600元，C1手动挡",
        "terms": ["4600"],
    },
    {
        "dim": "科目一",
        "q": "科目一考了多少？",
        "answer": "96分",
        "terms": ["96"],
    },
    {
        "dim": "科目二",
        "q": "科目二补考是什么时候？考了多少？",
        "answer": "4月5日，90分",
        "terms": ["90"],
    },
    {
        "dim": "驾照领取",
        "q": "什么时候拿到驾照？",
        "answer": "6月20日",
        "terms": ["20"],
    },
    {
        "dim": "未来安排",
        "q": "下次陪练是什么时候？",
        "answer": "8月10日",
        "terms": ["10"],
    },
    {
        "dim": "陪练记录",
        "q": "第一次上路陪练是什么时候？",
        "answer": "7月20日",
        "terms": ["20"],
    },
    {
        "dim": "驾校信息",
        "q": "驾校在哪？教练电话多少？",
        "answer": "城北训练场，138-2222-3333",
        "terms": ["城北", "3333"],
    },
    {
        "dim": "及格规则",
        "q": "科目一多少分及格？",
        "answer": "90分",
        "terms": ["90"],
    },
    {
        "dim": "换证提醒",
        "q": "驾照换证体检什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "科目三",
        "q": "科目三考了多少？",
        "answer": "100分",
        "terms": ["100"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="驾校学车",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="driving_mem0db",
        out_name="driving_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
