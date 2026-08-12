"""Documents & safe spot-check (round 310): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买保险柜。",
        "kind": "episodic",
        "cues": ["2026-01-10", "保险柜"],
    },
    {
        "content": "2026年1月20日放重要证件：户口本、房产证。",
        "kind": "semantic",
        "cues": ["保险柜", "房产证"],
    },
    {
        "content": "2026年2月1日办护照：2 月 15 日领取。",
        "kind": "episodic",
        "cues": ["2026-02-01", "护照"],
    },
    {
        "content": "2026年2月15日领护照。",
        "kind": "episodic",
        "cues": ["2026-02-15", "护照"],
    },
    {
        "content": "2026年3月1日证件复印件：准备 3 份。",
        "kind": "episodic",
        "cues": ["2026-03-01", "复印件"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日办港澳通行证。",
        "kind": "episodic",
        "cues": ["2026-03-15", "通行证"],
    },
    {
        "content": "2026年3月25日通行证办好。",
        "kind": "episodic",
        "cues": ["2026-03-25", "通行证"],
    },
    {
        "content": "2026年4月1日证件照：蓝底 1 寸。",
        "kind": "semantic",
        "cues": ["证件照", "蓝底"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日换驾驶证。",
        "kind": "episodic",
        "cues": ["2026-04-15", "驾驶证"],
    },
    {
        "content": "2026年4月25日驾驶证换好。",
        "kind": "episodic",
        "cues": ["2026-04-25", "驾驶证"],
    },
    {
        "content": "2026年5月1日证件到期检查：5 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-05-01", "检查"],
    },
    {
        "content": "2026年5月20日检查完成。",
        "kind": "episodic",
        "cues": ["2026-05-20", "检查"],
    },
    {
        "content": "2026年6月1日档案存放。",
        "kind": "episodic",
        "cues": ["2026-06-01", "档案"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日办无犯罪记录证明。",
        "kind": "episodic",
        "cues": ["2026-06-15", "无犯罪记录"],
    },
    {
        "content": "2026年6月25日证明拿到。",
        "kind": "episodic",
        "cues": ["2026-06-25", "无犯罪记录"],
    },
    {
        "content": "2026年7月1日证件电子版：扫描存档。",
        "kind": "semantic",
        "cues": ["电子版", "扫描"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日补办社保卡。",
        "kind": "episodic",
        "cues": ["2026-07-15", "社保卡"],
    },
    {
        "content": "2026年7月25日社保卡补好。",
        "kind": "episodic",
        "cues": ["2026-07-25", "社保卡"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日办签证材料。",
        "kind": "episodic",
        "cues": ["2026-08-01", "签证"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日证件照重拍。",
        "kind": "episodic",
        "cues": ["2026-08-05", "证件照"],
    },
]


QUESTIONS = [
    {
        "dim": "保险柜",
        "q": "保险柜里放了什么？",
        "answer": "户口本、房产证",
        "terms": ["房产证"],
    },
    {
        "dim": "护照",
        "q": "护照什么时候领的？",
        "answer": "2月15日",
        "terms": ["15"],
    },
    {
        "dim": "通行证",
        "q": "港澳通行证什么时候办好的？",
        "answer": "3月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次办签证材料是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "驾驶证",
        "q": "驾驶证什么时候换的？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "无犯罪记录",
        "q": "无犯罪记录证明什么时候拿到的？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "社保卡",
        "q": "社保卡什么时候补办的？",
        "answer": "7月25日",
        "terms": ["25"],
    },
    {
        "dim": "证件照",
        "q": "证件照什么底？多大？",
        "answer": "蓝底1寸",
        "terms": ["蓝底"],
    },
    {
        "dim": "电子版",
        "q": "证件电子版怎么存的？",
        "answer": "扫描存档",
        "terms": ["扫描"],
    },
    {
        "dim": "重拍提醒",
        "q": "证件照什么时候重拍？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="证件管理",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="documents_mem0db",
        out_name="documents_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
