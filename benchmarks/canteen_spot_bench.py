"""Community-canteen spot-check (round 330): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日社区食堂开业。",
        "kind": "episodic",
        "cues": ["2026-01-10", "食堂"],
    },
    {
        "content": "2026年1月20日第一次去食堂。",
        "kind": "episodic",
        "cues": ["2026-01-20", "食堂"],
    },
    {
        "content": "2026年2月1日办饭卡。",
        "kind": "episodic",
        "cues": ["2026-02-01", "饭卡"],
    },
    {
        "content": "2026年2月15日充值：200 元。",
        "kind": "episodic",
        "cues": ["2026-02-15", "充值"],
    },
    {
        "content": "2026年3月1日食堂菜单：周一红烧肉。",
        "kind": "semantic",
        "cues": ["菜单", "红烧肉"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日包间。",
        "kind": "episodic",
        "cues": ["2026-03-15", "包间"],
    },
    {
        "content": "2026年3月25日包间用餐。",
        "kind": "episodic",
        "cues": ["2026-03-25", "包间"],
    },
    {
        "content": "2026年4月1日饭卡余额：160 元。",
        "kind": "semantic",
        "cues": ["饭卡", "160"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日食堂活动。",
        "kind": "episodic",
        "cues": ["2026-04-15", "活动"],
    },
    {
        "content": "2026年4月25日活动完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "活动"],
    },
    {
        "content": "2026年5月1日食堂涨价：每份 2 元。",
        "kind": "episodic",
        "cues": ["2026-05-01", "涨价"],
    },
    {
        "content": "2026年5月15日预约 5 月 25 日端午节套餐。",
        "kind": "episodic",
        "cues": ["2026-05-15", "套餐"],
    },
    {
        "content": "2026年5月25日套餐领取。",
        "kind": "episodic",
        "cues": ["2026-05-25", "套餐"],
    },
    {
        "content": "2026年6月1日预约 6 月 15 日食堂卫生检查。",
        "kind": "episodic",
        "cues": ["2026-06-01", "卫生"],
    },
    {
        "content": "2026年6月15日检查通过。",
        "kind": "episodic",
        "cues": ["2026-06-15", "卫生"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日食堂菜单投票。",
        "kind": "episodic",
        "cues": ["2026-07-01", "投票"],
    },
    {
        "content": "2026年7月15日投票完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "投票"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日充值。",
        "kind": "episodic",
        "cues": ["2026-08-01", "充值"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日饭卡到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "饭卡"],
    },
    {
        "content": "食堂电话 400-222-6666。",
        "kind": "semantic",
        "cues": ["食堂", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "饭卡办理",
        "q": "饭卡什么时候办的？",
        "answer": "2月1日",
        "terms": ["1"],
    },
    {
        "dim": "充值记录",
        "q": "充值了多少钱？",
        "answer": "200元",
        "terms": ["200"],
    },
    {
        "dim": "食堂菜单",
        "q": "周一吃什么？",
        "answer": "红烧肉",
        "terms": ["红烧肉"],
    },
    {
        "dim": "未来安排",
        "q": "下次充值是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "饭卡余额",
        "q": "饭卡余额多少？",
        "answer": "160元",
        "terms": ["160"],
    },
    {
        "dim": "包间",
        "q": "包间什么时候用餐？",
        "answer": "3月25日",
        "terms": ["25"],
    },
    {
        "dim": "卫生检查",
        "q": "食堂卫生检查什么时候？过了吗？",
        "answer": "6月15日，通过",
        "terms": ["通过"],
    },
    {
        "dim": "食堂电话",
        "q": "食堂电话多少？",
        "answer": "400-222-6666",
        "terms": ["6666"],
    },
    {
        "dim": "涨价记录",
        "q": "食堂什么时候涨价的？",
        "answer": "5月1日",
        "terms": ["1"],
    },
    {
        "dim": "饭卡到期",
        "q": "饭卡什么时候到期？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="社区食堂",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="canteen_mem0db",
        out_name="canteen_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
