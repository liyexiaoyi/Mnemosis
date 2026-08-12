"""Home-gym-gear spot-check (round 321): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买瑜伽垫。",
        "kind": "episodic",
        "cues": ["2026-01-10", "瑜伽垫"],
    },
    {
        "content": "2026年1月20日买哑铃套装。",
        "kind": "episodic",
        "cues": ["2026-01-20", "哑铃"],
    },
    {
        "content": "2026年2月1日买跑步机：家用款。",
        "kind": "episodic",
        "cues": ["2026-02-01", "跑步机"],
    },
    {
        "content": "2026年2月15日跑步机安装。",
        "kind": "episodic",
        "cues": ["2026-02-15", "跑步机"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日跑步机保养。",
        "kind": "episodic",
        "cues": ["2026-03-01", "保养"],
    },
    {
        "content": "2026年3月15日保养完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "保养"],
    },
    {
        "content": "2026年4月1日哑铃脱漆，4 月 5 日换新。",
        "kind": "episodic",
        "cues": ["2026-04-01", "脱漆"],
    },
    {
        "content": "2026年4月5日换新完成。",
        "kind": "episodic",
        "cues": ["2026-04-05", "换新"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日体脂秤校准。",
        "kind": "episodic",
        "cues": ["2026-05-01", "体脂秤"],
    },
    {
        "content": "2026年5月15日校准完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "体脂秤"],
    },
    {
        "content": "2026年6月1日买弹力带。",
        "kind": "episodic",
        "cues": ["2026-06-01", "弹力带"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日跑步机检修。",
        "kind": "episodic",
        "cues": ["2026-06-15", "检修"],
    },
    {
        "content": "2026年6月25日检修完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "检修"],
    },
    {
        "content": "2026年7月1日买泡沫轴。",
        "kind": "episodic",
        "cues": ["2026-07-01", "泡沫轴"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日瑜伽课。",
        "kind": "episodic",
        "cues": ["2026-07-15", "瑜伽课"],
    },
    {
        "content": "2026年7月25日瑜伽课完成。",
        "kind": "episodic",
        "cues": ["2026-07-25", "瑜伽课"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日买新跑步机。",
        "kind": "episodic",
        "cues": ["2026-08-01", "跑步机"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日换跑步机油。",
        "kind": "episodic",
        "cues": ["2026-08-05", "机油"],
    },
    {
        "content": "健身器材店电话 400-222-9999。",
        "kind": "semantic",
        "cues": ["器材店", "电话"],
    },
    {
        "content": "跑步机位置：客厅角落。",
        "kind": "semantic",
        "cues": ["跑步机", "位置"],
    },
]


QUESTIONS = [
    {
        "dim": "健身器材",
        "q": "买了什么健身器材？",
        "answer": "弹力带",
        "terms": ["弹力带"],
    },
    {
        "dim": "跑步机购买",
        "q": "跑步机什么时候买的？",
        "answer": "2月1日",
        "terms": ["1"],
    },
    {
        "dim": "跑步机保养",
        "q": "跑步机什么时候保养的？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "未来安排",
        "q": "下次买新跑步机是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "哑铃换新",
        "q": "哑铃什么时候换新的？",
        "answer": "4月5日",
        "terms": ["5"],
    },
    {
        "dim": "体脂秤",
        "q": "体脂秤什么时候校准的？",
        "answer": "5月15日",
        "terms": ["15"],
    },
    {
        "dim": "跑步机检修",
        "q": "跑步机什么时候检修的？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "瑜伽课",
        "q": "瑜伽课什么时候？",
        "answer": "7月25日",
        "terms": ["25"],
    },
    {
        "dim": "器材店",
        "q": "器材店电话多少？",
        "answer": "400-222-9999",
        "terms": ["9999"],
    },
    {
        "dim": "换机油",
        "q": "什么时候换跑步机油？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭健身器材",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="gymgear_mem0db",
        out_name="gymgear_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
