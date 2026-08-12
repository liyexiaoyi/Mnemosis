"""Community-neighbor spot-check (round 319): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日搬进新小区。",
        "kind": "episodic",
        "cues": ["2026-01-10", "搬家"],
    },
    {
        "content": "2026年1月20日认识邻居张阿姨。",
        "kind": "semantic",
        "cues": ["邻居", "张阿姨"],
    },
    {
        "content": "2026年2月1日加入业主群。",
        "kind": "episodic",
        "cues": ["2026-02-01", "业主群"],
    },
    {
        "content": "2026年2月15日借给邻居工具。",
        "kind": "episodic",
        "cues": ["2026-02-15", "工具"],
    },
    {
        "content": "2026年3月1日邻居帮忙收快递。",
        "kind": "episodic",
        "cues": ["2026-03-01", "收快递"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日邻里聚餐。",
        "kind": "episodic",
        "cues": ["2026-03-15", "聚餐"],
    },
    {
        "content": "2026年3月25日聚餐完成。",
        "kind": "episodic",
        "cues": ["2026-03-25", "聚餐"],
    },
    {
        "content": "2026年4月1日业主大会：4 月 15 日。",
        "kind": "episodic",
        "cues": ["2026-04-01", "业主大会"],
    },
    {
        "content": "2026年4月15日业主大会参加。",
        "kind": "episodic",
        "cues": ["2026-04-15", "业主大会"],
    },
    {
        "content": "2026年5月1日帮邻居照看猫。",
        "kind": "episodic",
        "cues": ["2026-05-01", "照看猫"],
    },
    {
        "content": "2026年5月20日预约 5 月 30 日社区义诊。",
        "kind": "episodic",
        "cues": ["2026-05-20", "义诊"],
    },
    {
        "content": "2026年5月30日义诊完成。",
        "kind": "episodic",
        "cues": ["2026-05-30", "义诊"],
    },
    {
        "content": "2026年6月1日邻里互助群。",
        "kind": "semantic",
        "cues": ["互助群"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日跳蚤市场。",
        "kind": "episodic",
        "cues": ["2026-06-15", "跳蚤市场"],
    },
    {
        "content": "2026年6月25日跳蚤市场摆摊。",
        "kind": "episodic",
        "cues": ["2026-06-25", "摆摊"],
    },
    {
        "content": "2026年7月1日邻居李叔家水管爆。",
        "kind": "episodic",
        "cues": ["2026-07-01", "李叔"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日小区清洁日。",
        "kind": "episodic",
        "cues": ["2026-07-15", "清洁日"],
    },
    {
        "content": "2026年7月25日清洁日完成。",
        "kind": "episodic",
        "cues": ["2026-07-25", "清洁日"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日邻里读书会。",
        "kind": "episodic",
        "cues": ["2026-08-01", "读书会"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日业主缴费。",
        "kind": "episodic",
        "cues": ["2026-08-05", "缴费"],
    },
    {
        "content": "物业电话 400-555-1111。",
        "kind": "semantic",
        "cues": ["物业", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "邻居认识",
        "q": "认识了哪位邻居？",
        "answer": "张阿姨",
        "terms": ["张阿姨"],
    },
    {
        "dim": "邻居帮忙",
        "q": "邻居帮了什么忙？",
        "answer": "收快递",
        "terms": ["快递"],
    },
    {
        "dim": "邻里聚餐",
        "q": "邻里聚餐什么时候？",
        "answer": "3月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次读书会是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "业主大会",
        "q": "业主大会什么时候？",
        "answer": "4月15日",
        "terms": ["15"],
    },
    {
        "dim": "社区义诊",
        "q": "社区义诊什么时候？",
        "answer": "5月30日",
        "terms": ["30"],
    },
    {
        "dim": "跳蚤市场",
        "q": "跳蚤市场摆摊什么时候？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "清洁日",
        "q": "小区清洁日什么时候？",
        "answer": "7月25日",
        "terms": ["25"],
    },
    {
        "dim": "物业电话",
        "q": "物业电话多少？",
        "answer": "400-555-1111",
        "terms": ["1111"],
    },
    {
        "dim": "业主缴费",
        "q": "业主什么时候缴费？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="社区邻里",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="neighbor_mem0db",
        out_name="neighbor_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
