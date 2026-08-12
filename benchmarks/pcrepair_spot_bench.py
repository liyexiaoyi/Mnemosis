"""PC-repair-shop spot-check (round 346): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日第一次送电脑维修，换固态硬盘300元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "维修"],
    },
    {
        "content": "2026年1月14日取回电脑。",
        "kind": "episodic",
        "cues": ["2026-01-14", "取机"],
    },
    {
        "content": "维修店营业时间：早9点到晚9点。",
        "kind": "semantic",
        "cues": ["营业时间", "9点"],
    },
    {
        "content": "维修店电话 0731-6666-1111。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "维修项目：换屏、清灰、重装系统、数据恢复。",
        "kind": "semantic",
        "cues": ["项目", "换屏"],
    },
    {
        "content": "保修说明：维修部件保修3个月。",
        "kind": "semantic",
        "cues": ["保修", "3个月"],
    },
    {
        "content": "2026年2月5日预约2月18日清灰服务。",
        "kind": "episodic",
        "cues": ["2026-02-05", "清灰"],
    },
    {
        "content": "2026年2月18日清灰完成，费用80元。",
        "kind": "episodic",
        "cues": ["2026-02-18", "清灰"],
    },
    {
        "content": "数据备份说明：维修前免费备份数据。",
        "kind": "semantic",
        "cues": ["备份", "说明"],
    },
    {
        "content": "2026年3月10日购买键盘配件180元。",
        "kind": "episodic",
        "cues": ["2026-03-10", "键盘"],
    },
    {
        "content": "2026年3月18日键盘更换完成。",
        "kind": "episodic",
        "cues": ["2026-03-18", "键盘"],
    },
    {
        "content": "2026年4月8日收到通知：4月22日会员日活动。",
        "kind": "episodic",
        "cues": ["2026-04-08", "会员日"],
    },
    {
        "content": "2026年4月22日会员日维修8折。",
        "kind": "episodic",
        "cues": ["2026-04-22", "会员日"],
    },
    {
        "content": "2026年5月6日预约5月20日数据恢复服务。",
        "kind": "episodic",
        "cues": ["2026-05-06", "数据恢复"],
    },
    {
        "content": "2026年5月20日数据恢复完成，找回照片。",
        "kind": "episodic",
        "cues": ["2026-05-20", "数据恢复"],
    },
    {
        "content": "2026年6月12日收到通知：6月26日夏季清灰优惠。",
        "kind": "episodic",
        "cues": ["2026-06-12", "优惠"],
    },
    {
        "content": "2026年6月26日清灰优惠活动完成。",
        "kind": "episodic",
        "cues": ["2026-06-26", "优惠"],
    },
    {
        "content": "2026年7月9日预约7月23日重装系统。",
        "kind": "episodic",
        "cues": ["2026-07-09", "重装"],
    },
    {
        "content": "2026年7月23日重装完成，费用150元。",
        "kind": "episodic",
        "cues": ["2026-07-23", "重装"],
    },
    {
        "content": "2026年8月4日预约8月17日取机。",
        "kind": "episodic",
        "cues": ["2026-08-04", "取机"],
    },
]


QUESTIONS = [
    {
        "dim": "首次维修",
        "q": "第一次送电脑维修是什么时候？",
        "answer": "1月10日",
        "terms": ["10"],
    },
    {
        "dim": "换硬盘费用",
        "q": "换固态硬盘多少钱？",
        "answer": "300元",
        "terms": ["300"],
    },
    {
        "dim": "下次取机",
        "q": "下次取机是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "维修店几点关门？",
        "answer": "晚9点",
        "terms": ["9"],
    },
    {
        "dim": "电话",
        "q": "维修店电话多少？",
        "answer": "0731-6666-1111",
        "terms": ["1111"],
    },
    {
        "dim": "维修项目",
        "q": "维修店能修哪些项目？",
        "answer": "换屏、清灰、重装系统、数据恢复",
        "terms": ["数据恢复"],
    },
    {
        "dim": "保修",
        "q": "维修部件保修多久？",
        "answer": "3个月",
        "terms": ["3个月"],
    },
    {
        "dim": "备份说明",
        "q": "维修前数据怎么处理？",
        "answer": "免费备份",
        "terms": ["备份"],
    },
    {
        "dim": "会员日优惠",
        "q": "会员日维修打几折？",
        "answer": "8折",
        "terms": ["8"],
    },
    {
        "dim": "数据恢复",
        "q": "数据恢复什么时候完成的？",
        "answer": "5月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="电脑维修店",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="pcrepair_mem0db",
        out_name="pcrepair_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
