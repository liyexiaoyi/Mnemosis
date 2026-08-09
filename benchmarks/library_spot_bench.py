"""Library-borrowing spot-check (round 283): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日办借书卡：押金 100 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "借书卡"],
    },
    {
        "content": "2026年1月15日借《人类简史》，2 月 15 日到期。",
        "kind": "episodic",
        "cues": ["2026-01-15", "人类简史"],
    },
    {
        "content": "2026年2月10日还书并续借《三体》。",
        "kind": "episodic",
        "cues": ["2026-02-10", "三体"],
    },
    {
        "content": "2026年2月20日借《三体2》，3 月 20 日到期。",
        "kind": "episodic",
        "cues": ["2026-02-20", "三体2"],
    },
    {
        "content": "2026年3月15日还书。",
        "kind": "episodic",
        "cues": ["2026-03-15", "还书"],
    },
    {
        "content": "2026年4月1日预约 4 月 10 日借《百年孤独》。",
        "kind": "episodic",
        "cues": ["2026-04-01", "百年孤独"],
    },
    {
        "content": "2026年4月10日取书。",
        "kind": "episodic",
        "cues": ["2026-04-10", "取书"],
    },
    {
        "content": "2026年5月1日图书馆装修，5 月 20 日恢复。",
        "kind": "episodic",
        "cues": ["2026-05-01", "装修"],
    },
    {
        "content": "2026年5月20日恢复开放。",
        "kind": "episodic",
        "cues": ["2026-05-20", "开放"],
    },
    {
        "content": "2026年6月1日借《思考快与慢》。",
        "kind": "episodic",
        "cues": ["2026-06-01", "思考快与慢"],
    },
    {
        "content": "2026年6月15日还《思考快与慢》。",
        "kind": "episodic",
        "cues": ["2026-06-15", "还书"],
    },
    {
        "content": "2026年7月1日借《人类简史》新版。",
        "kind": "episodic",
        "cues": ["2026-07-01", "人类简史"],
    },
    {
        "content": "2026年7月10日收到提醒：7 月 20 日前还书。",
        "kind": "episodic",
        "cues": ["2026-07-10", "还书"],
    },
    {
        "content": "2026年7月20日还书。",
        "kind": "episodic",
        "cues": ["2026-07-20", "还书"],
    },
    {
        "content": "2026年8月1日借《原则》，8 月 30 日到期。",
        "kind": "episodic",
        "cues": ["2026-08-01", "原则"],
    },
    {
        "content": "2026年8月5日预约 8 月 15 日借《置身事内》。",
        "kind": "episodic",
        "cues": ["2026-08-05", "置身事内"],
    },
    {
        "content": "借书规则：每人最多 5 本，借期 30 天。",
        "kind": "semantic",
        "cues": ["借书规则"],
    },
    {
        "content": "逾期费：0.2 元/天。",
        "kind": "semantic",
        "cues": ["逾期费"],
    },
    {
        "content": "图书馆开放：周二到周日 9:00-18:00，周一闭馆。",
        "kind": "semantic",
        "cues": ["开放时间"],
    },
    {
        "content": "自助借还机在 1 楼大厅。",
        "kind": "semantic",
        "cues": ["借还机"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日图书馆讲座。",
        "kind": "episodic",
        "cues": ["2026-08-08", "讲座"],
    },
    {
        "content": "还书箱在门口。",
        "kind": "semantic",
        "cues": ["还书箱"],
    },
    {
        "content": "电子书账号：读者证号 20260110。",
        "kind": "semantic",
        "cues": ["读者证", "20260110"],
    },
    {
        "content": "2026年8月9日预约 8 月 18 日借《枪炮病菌与钢铁》。",
        "kind": "episodic",
        "cues": ["2026-08-09", "枪炮"],
    },
]


QUESTIONS = [
    {
        "dim": "借阅记录",
        "q": "上次借了什么书？",
        "answer": "《原则》",
        "terms": ["原则"],
    },
    {
        "dim": "未来安排",
        "q": "下次预约借书是什么时候？借什么？",
        "answer": "8月15日，置身事内",
        "terms": ["置身事内"],
    },
    {
        "dim": "还书记录",
        "q": "上次还书是什么时候？",
        "answer": "7月20日",
        "terms": ["20"],
    },
    {
        "dim": "借书卡",
        "q": "借书卡押金多少？",
        "answer": "100元",
        "terms": ["100"],
    },
    {
        "dim": "到期时间",
        "q": "《原则》什么时候到期？",
        "answer": "8月30日",
        "terms": ["30"],
    },
    {
        "dim": "借阅规则",
        "q": "一次能借几本？借多久？",
        "answer": "5本，30天",
        "terms": ["5", "30"],
    },
    {
        "dim": "逾期费用",
        "q": "逾期费多少？",
        "answer": "0.2元/天",
        "terms": ["0.2"],
    },
    {
        "dim": "开放时间",
        "q": "图书馆什么时候开放？",
        "answer": "周二到周日9:00-18:00，周一闭馆",
        "terms": ["18"],
    },
    {
        "dim": "讲座通知",
        "q": "图书馆讲座什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "读者证",
        "q": "读者证号多少？",
        "answer": "20260110",
        "terms": ["20260110"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="图书馆借阅",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="library_mem0db",
        out_name="library_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
