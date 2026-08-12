"""Parcel-station spot-check (round 292): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日小区新开菜鸟驿站。",
        "kind": "episodic",
        "cues": ["2026-01-10", "驿站"],
    },
    {
        "content": "2026年1月15日第一次取件：取件码 1122。",
        "kind": "episodic",
        "cues": ["2026-01-15", "取件码"],
    },
    {
        "content": "2026年2月1日寄件：寄给爸妈，顺丰 23 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "寄件"],
    },
    {
        "content": "2026年2月15日包裹滞留，驿站提醒 3 天不取退回。",
        "kind": "episodic",
        "cues": ["2026-02-15", "滞留"],
    },
    {
        "content": "2026年3月1日开通驿站会员：代收 8 元/月。",
        "kind": "episodic",
        "cues": ["2026-03-01", "会员"],
    },
    {
        "content": "2026年3月15日大件送货上门。",
        "kind": "episodic",
        "cues": ["2026-03-15", "大件"],
    },
    {
        "content": "2026年4月1日寄件涨价：首重 12 元。",
        "kind": "episodic",
        "cues": ["2026-04-01", "涨价"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日寄大件。",
        "kind": "episodic",
        "cues": ["2026-04-15", "寄大件"],
    },
    {
        "content": "2026年4月25日寄大件：50kg，85 元。",
        "kind": "episodic",
        "cues": ["2026-04-25", "寄大件"],
    },
    {
        "content": "2026年5月1日驿站营业时间改到 21:00。",
        "kind": "semantic",
        "cues": ["营业时间"],
    },
    {
        "content": "2026年5月15日收到快递破损，申请赔偿。",
        "kind": "episodic",
        "cues": ["2026-05-15", "赔偿"],
    },
    {
        "content": "2026年5月25日赔偿到账 150 元。",
        "kind": "episodic",
        "cues": ["2026-05-25", "赔偿"],
    },
    {
        "content": "2026年6月1日取件码规则：保留 3 天。",
        "kind": "semantic",
        "cues": ["取件码规则"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日退货取件。",
        "kind": "episodic",
        "cues": ["2026-06-15", "退货取件"],
    },
    {
        "content": "2026年6月25日退货取件完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "退货取件"],
    },
    {
        "content": "2026年7月1日驿站换老板。",
        "kind": "episodic",
        "cues": ["2026-07-01", "换老板"],
    },
    {
        "content": "2026年7月15日新老板电话 400-999-8888。",
        "kind": "semantic",
        "cues": ["老板", "电话"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日寄生日礼物。",
        "kind": "episodic",
        "cues": ["2026-08-01", "生日礼物"],
    },
    {
        "content": "2026年8月5日收到通知：8 月 20 日驿站搬家。",
        "kind": "episodic",
        "cues": ["2026-08-05", "搬家"],
    },
    {
        "content": "驿站地址：小区东门。",
        "kind": "semantic",
        "cues": ["地址", "东门"],
    },
]


QUESTIONS = [
    {
        "dim": "驿站地址",
        "q": "驿站现在在哪？",
        "answer": "小区东门",
        "terms": ["东门"],
    },
    {
        "dim": "寄件费用",
        "q": "寄件首重多少钱？",
        "answer": "12元",
        "terms": ["12"],
    },
    {
        "dim": "寄件记录",
        "q": "上次寄大件是什么时候？多少钱？",
        "answer": "4月25日，85元",
        "terms": ["85"],
    },
    {
        "dim": "赔偿记录",
        "q": "上次快递赔偿到账多少？",
        "answer": "150元",
        "terms": ["150"],
    },
    {
        "dim": "未来安排",
        "q": "下次寄生日礼物是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "取件规则",
        "q": "取件码保留几天？",
        "answer": "3天",
        "terms": ["3"],
    },
    {
        "dim": "会员费用",
        "q": "驿站会员多少钱？",
        "answer": "8元/月",
        "terms": ["8"],
    },
    {
        "dim": "老板电话",
        "q": "新老板电话多少？",
        "answer": "400-999-8888",
        "terms": ["8888"],
    },
    {
        "dim": "营业时间",
        "q": "驿站营业到几点？",
        "answer": "21:00",
        "terms": ["21"],
    },
    {
        "dim": "滞留规则",
        "q": "包裹不取几天退回？",
        "answer": "3天",
        "terms": ["3"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="快递驿站",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="parcel_mem0db",
        out_name="parcel_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
