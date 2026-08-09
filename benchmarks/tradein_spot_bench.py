"""Trade-in spot-check (round 325): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日预约 1 月 20 日以旧换新。",
        "kind": "episodic",
        "cues": ["2026-01-10", "以旧换新"],
    },
    {
        "content": "2026年1月20日旧冰箱抵 300。",
        "kind": "episodic",
        "cues": ["2026-01-20", "冰箱"],
    },
    {
        "content": "2026年2月1日买新冰箱：以旧换新价 4200。",
        "kind": "episodic",
        "cues": ["2026-02-01", "冰箱"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日旧洗衣机。",
        "kind": "episodic",
        "cues": ["2026-02-15", "洗衣机"],
    },
    {
        "content": "2026年2月25日旧洗衣机抵 200。",
        "kind": "episodic",
        "cues": ["2026-02-25", "洗衣机"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日补贴申请。",
        "kind": "episodic",
        "cues": ["2026-03-01", "补贴"],
    },
    {
        "content": "2026年3月15日补贴到账 500。",
        "kind": "episodic",
        "cues": ["2026-03-15", "补贴"],
    },
    {
        "content": "2026年4月1日买新洗衣机：抵扣后 2600。",
        "kind": "episodic",
        "cues": ["2026-04-01", "洗衣机"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日旧空调。",
        "kind": "episodic",
        "cues": ["2026-04-15", "空调"],
    },
    {
        "content": "2026年4月25日旧空调抵 400。",
        "kind": "episodic",
        "cues": ["2026-04-25", "空调"],
    },
    {
        "content": "2026年5月1日买新空调：抵扣后 3200。",
        "kind": "episodic",
        "cues": ["2026-05-01", "空调"],
    },
    {
        "content": "2026年5月15日预约 5 月 25 日旧电视。",
        "kind": "episodic",
        "cues": ["2026-05-15", "电视"],
    },
    {
        "content": "2026年5月25日旧电视抵 150。",
        "kind": "episodic",
        "cues": ["2026-05-25", "电视"],
    },
    {
        "content": "2026年6月1日买新电视：抵扣后 1800。",
        "kind": "episodic",
        "cues": ["2026-06-01", "电视"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日旧手机。",
        "kind": "episodic",
        "cues": ["2026-06-15", "手机"],
    },
    {
        "content": "2026年6月25日旧手机抵 800。",
        "kind": "episodic",
        "cues": ["2026-06-25", "手机"],
    },
    {
        "content": "2026年7月1日买新手机：抵扣后 5200。",
        "kind": "episodic",
        "cues": ["2026-07-01", "手机"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日旧电脑。",
        "kind": "episodic",
        "cues": ["2026-08-01", "电脑"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日补贴到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "补贴"],
    },
    {
        "content": "换新客服 400-444-6666。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "新冰箱",
        "q": "新冰箱抵扣后多少钱？",
        "answer": "4200元",
        "terms": ["4200"],
    },
    {
        "dim": "旧冰箱",
        "q": "旧冰箱抵了多少？",
        "answer": "300元",
        "terms": ["300"],
    },
    {
        "dim": "洗衣机换新",
        "q": "旧洗衣机抵多少？新洗衣机多少钱？",
        "answer": "200元，2600元",
        "terms": ["2600"],
    },
    {
        "dim": "未来安排",
        "q": "下次旧电脑换新是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "补贴记录",
        "q": "补贴什么时候到账？多少？",
        "answer": "3月15日，500元",
        "terms": ["500"],
    },
    {
        "dim": "旧空调",
        "q": "旧空调抵多少？",
        "answer": "400元",
        "terms": ["400"],
    },
    {
        "dim": "新电视",
        "q": "新电视抵扣后多少钱？",
        "answer": "1800元",
        "terms": ["1800"],
    },
    {
        "dim": "旧手机",
        "q": "旧手机抵多少？",
        "answer": "800元",
        "terms": ["800"],
    },
    {
        "dim": "换新客服",
        "q": "换新客服电话多少？",
        "answer": "400-444-6666",
        "terms": ["6666"],
    },
    {
        "dim": "补贴到期",
        "q": "补贴什么时候到期？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="以旧换新",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="tradein_mem0db",
        out_name="tradein_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
