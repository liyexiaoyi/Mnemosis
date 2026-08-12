"""Home-ledger spot-check (round 303): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日开始记账。",
        "kind": "episodic",
        "cues": ["2026-01-10", "记账"],
    },
    {
        "content": "2026年1月20日1 月支出：6850 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "支出"],
    },
    {
        "content": "2026年2月1日预算：每月 6000 元。",
        "kind": "semantic",
        "cues": ["预算", "6000"],
    },
    {
        "content": "2026年2月15日2 月支出：5900 元。",
        "kind": "episodic",
        "cues": ["2026-02-15", "支出"],
    },
    {
        "content": "2026年3月1日记账软件：随手记。",
        "kind": "semantic",
        "cues": ["记账软件", "随手记"],
    },
    {
        "content": "2026年3月15日3 月支出：7200 元，超预算。",
        "kind": "episodic",
        "cues": ["2026-03-15", "支出"],
    },
    {
        "content": "2026年4月1日调整预算：6500 元。",
        "kind": "semantic",
        "cues": ["预算", "6500"],
    },
    {
        "content": "2026年4月15日4 月支出：6100 元。",
        "kind": "episodic",
        "cues": ["2026-04-15", "支出"],
    },
    {
        "content": "2026年5月1日预约 5 月 10 日对账。",
        "kind": "episodic",
        "cues": ["2026-05-01", "对账"],
    },
    {
        "content": "2026年5月10日对账完成。",
        "kind": "episodic",
        "cues": ["2026-05-10", "对账"],
    },
    {
        "content": "2026年6月1日6 月支出预测。",
        "kind": "episodic",
        "cues": ["2026-06-01", "预测"],
    },
    {
        "content": "2026年6月15日半年总结：总支出 3.6 万。",
        "kind": "episodic",
        "cues": ["2026-06-15", "半年总结"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日理财复盘。",
        "kind": "episodic",
        "cues": ["2026-07-01", "复盘"],
    },
    {
        "content": "2026年7月10日复盘完成。",
        "kind": "episodic",
        "cues": ["2026-07-10", "复盘"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日做下季度预算。",
        "kind": "episodic",
        "cues": ["2026-08-01", "预算"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日交房租。",
        "kind": "episodic",
        "cues": ["2026-08-05", "房租"],
    },
    {
        "content": "记账分类：餐饮、交通、住房。",
        "kind": "semantic",
        "cues": ["分类"],
    },
    {
        "content": "记账时间：每晚 9 点。",
        "kind": "semantic",
        "cues": ["记账时间"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日记账讲座。",
        "kind": "episodic",
        "cues": ["2026-08-08", "讲座"],
    },
]


QUESTIONS = [
    {
        "dim": "预算金额",
        "q": "现在每月预算多少？",
        "answer": "6500元",
        "terms": ["6500"],
    },
    {
        "dim": "超支记录",
        "q": "哪个月超预算了？",
        "answer": "3月",
        "terms": ["7200"],
    },
    {
        "dim": "半年总结",
        "q": "半年总支出多少？",
        "answer": "3.6万",
        "terms": ["3.6"],
    },
    {
        "dim": "未来安排",
        "q": "下次做预算是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "对账记录",
        "q": "上次对账是什么时候？",
        "answer": "5月10日",
        "terms": ["10"],
    },
    {
        "dim": "复盘记录",
        "q": "理财复盘什么时候？",
        "answer": "7月10日",
        "terms": ["10"],
    },
    {
        "dim": "记账分类",
        "q": "记账分几类？",
        "answer": "餐饮、交通、住房",
        "terms": ["住房"],
    },
    {
        "dim": "记账时间",
        "q": "每天几点记账？",
        "answer": "晚9点",
        "terms": ["9"],
    },
    {
        "dim": "记账软件",
        "q": "用什么记账软件？",
        "answer": "随手记",
        "terms": ["随手记"],
    },
    {
        "dim": "房租提醒",
        "q": "什么时候交房租？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭记账",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="ledger_mem0db",
        out_name="ledger_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
