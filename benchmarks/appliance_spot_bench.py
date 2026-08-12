"""Home-appliance spot-check (round 301): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买冰箱：海尔 4599 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "冰箱"],
    },
    {
        "content": "2026年1月20日买洗衣机：小天鹅 2899 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "洗衣机"],
    },
    {
        "content": "2026年2月1日买烤箱：美的 799 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "烤箱"],
    },
    {
        "content": "2026年2月15日冰箱制冷弱，2 月 20 日报修。",
        "kind": "episodic",
        "cues": ["2026-02-15", "报修"],
    },
    {
        "content": "2026年2月20日报修完成。",
        "kind": "episodic",
        "cues": ["2026-02-20", "报修"],
    },
    {
        "content": "2026年3月1日洗衣机异响，3 月 5 日检修。",
        "kind": "episodic",
        "cues": ["2026-03-01", "异响"],
    },
    {
        "content": "2026年3月5日检修完成。",
        "kind": "episodic",
        "cues": ["2026-03-05", "检修"],
    },
    {
        "content": "2026年4月1日烤箱首次使用。",
        "kind": "episodic",
        "cues": ["2026-04-01", "烤箱"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日清洗空调。",
        "kind": "episodic",
        "cues": ["2026-04-15", "空调"],
    },
    {
        "content": "2026年4月25日清洗完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "空调"],
    },
    {
        "content": "2026年5月1日买空气炸锅：599 元。",
        "kind": "episodic",
        "cues": ["2026-05-01", "空气炸锅"],
    },
    {
        "content": "2026年5月15日微波炉换磁控管：5 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-05-15", "磁控管"],
    },
    {
        "content": "2026年5月20日换完。",
        "kind": "episodic",
        "cues": ["2026-05-20", "磁控管"],
    },
    {
        "content": "2026年6月1日预约 6 月 15 日热水器保养。",
        "kind": "episodic",
        "cues": ["2026-06-01", "热水器"],
    },
    {
        "content": "2026年6月15日保养完成。",
        "kind": "episodic",
        "cues": ["2026-06-15", "热水器"],
    },
    {
        "content": "2026年7月1日冰箱噪音，7 月 5 日检查。",
        "kind": "episodic",
        "cues": ["2026-07-01", "噪音"],
    },
    {
        "content": "2026年7月5日检查：正常。",
        "kind": "episodic",
        "cues": ["2026-07-05", "检查"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日洗衣机清洗。",
        "kind": "episodic",
        "cues": ["2026-08-01", "洗衣机"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日烤箱保修到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "保修"],
    },
    {
        "content": "家电客服 400-888-9999。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "购买记录",
        "q": "冰箱多少钱？",
        "answer": "4599元",
        "terms": ["4599"],
    },
    {
        "dim": "冰箱报修",
        "q": "冰箱什么时候报修的？修好了吗？",
        "answer": "2月20日，修好",
        "terms": ["20"],
    },
    {
        "dim": "洗衣机问题",
        "q": "洗衣机什么问题？什么时候检修的？",
        "answer": "异响，3月5日",
        "terms": ["异响"],
    },
    {
        "dim": "未来安排",
        "q": "下次洗衣机清洗是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "空调清洗",
        "q": "空调什么时候清洗的？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "微波炉维修",
        "q": "微波炉换的什么？",
        "answer": "磁控管",
        "terms": ["磁控管"],
    },
    {
        "dim": "热水器保养",
        "q": "热水器什么时候保养的？",
        "answer": "6月15日",
        "terms": ["15"],
    },
    {
        "dim": "保修到期",
        "q": "烤箱保修什么时候到期？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "空气炸锅",
        "q": "空气炸锅多少钱？",
        "answer": "599元",
        "terms": ["599"],
    },
    {
        "dim": "客服电话",
        "q": "家电客服电话多少？",
        "answer": "400-888-9999",
        "terms": ["9999"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家电使用",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="appliance_mem0db",
        out_name="appliance_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
