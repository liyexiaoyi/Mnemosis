"""Sports-gear spot-check (round 317): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日买跑鞋：亚瑟士 899 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "跑鞋"],
    },
    {
        "content": "2026年1月20日买运动服。",
        "kind": "episodic",
        "cues": ["2026-01-20", "运动服"],
    },
    {
        "content": "2026年2月1日第一次 5 公里跑。",
        "kind": "episodic",
        "cues": ["2026-02-01", "5公里"],
    },
    {
        "content": "2026年2月15日跑鞋磨脚，2 月 20 日换鞋垫。",
        "kind": "episodic",
        "cues": ["2026-02-15", "鞋垫"],
    },
    {
        "content": "2026年2月20日换鞋垫完成。",
        "kind": "episodic",
        "cues": ["2026-02-20", "鞋垫"],
    },
    {
        "content": "2026年3月1日报名半马：3 月 20 日截止。",
        "kind": "episodic",
        "cues": ["2026-03-01", "半马"],
    },
    {
        "content": "2026年3月20日报名成功。",
        "kind": "episodic",
        "cues": ["2026-03-20", "半马"],
    },
    {
        "content": "2026年4月1日预约 4 月 15 日体测。",
        "kind": "episodic",
        "cues": ["2026-04-01", "体测"],
    },
    {
        "content": "2026年4月15日体测完成。",
        "kind": "episodic",
        "cues": ["2026-04-15", "体测"],
    },
    {
        "content": "2026年5月1日买运动手表。",
        "kind": "episodic",
        "cues": ["2026-05-01", "手表"],
    },
    {
        "content": "2026年5月15日预约 5 月 25 日跑姿分析。",
        "kind": "episodic",
        "cues": ["2026-05-15", "跑姿"],
    },
    {
        "content": "2026年5月25日分析完成。",
        "kind": "episodic",
        "cues": ["2026-05-25", "跑姿"],
    },
    {
        "content": "2026年6月1日买能量胶。",
        "kind": "episodic",
        "cues": ["2026-06-01", "能量胶"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日长距离训练。",
        "kind": "episodic",
        "cues": ["2026-06-15", "长距离"],
    },
    {
        "content": "2026年6月25日训练完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "长距离"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日半马。",
        "kind": "episodic",
        "cues": ["2026-07-01", "半马"],
    },
    {
        "content": "2026年7月15日半马完成：2 小时 5 分。",
        "kind": "episodic",
        "cues": ["2026-07-15", "半马"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日买新跑鞋。",
        "kind": "episodic",
        "cues": ["2026-08-01", "跑鞋"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日拉伸课。",
        "kind": "episodic",
        "cues": ["2026-08-05", "拉伸课"],
    },
    {
        "content": "运动店电话 400-999-6666。",
        "kind": "semantic",
        "cues": ["运动店", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "跑鞋价格",
        "q": "跑鞋多少钱？",
        "answer": "899元",
        "terms": ["899"],
    },
    {
        "dim": "半马成绩",
        "q": "半马什么时候跑的？成绩多少？",
        "answer": "7月15日，2小时5分",
        "terms": ["小时"],
    },
    {
        "dim": "报名截止",
        "q": "半马报名什么时候截止？",
        "answer": "3月20日",
        "terms": ["20"],
    },
    {
        "dim": "未来安排",
        "q": "下次买新跑鞋是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "体测",
        "q": "体测什么时候？",
        "answer": "4月15日",
        "terms": ["15"],
    },
    {
        "dim": "跑姿分析",
        "q": "跑姿分析什么时候？",
        "answer": "5月25日",
        "terms": ["25"],
    },
    {
        "dim": "长距离训练",
        "q": "上次长距离训练是什么时候？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "运动装备",
        "q": "买了什么装备？",
        "answer": "运动手表",
        "terms": ["手表"],
    },
    {
        "dim": "拉伸课",
        "q": "拉伸课什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "补给品",
        "q": "买了什么补给？",
        "answer": "能量胶",
        "terms": ["能量胶"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="运动装备",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="sports_mem0db",
        out_name="sports_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
