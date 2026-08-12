"""Pet-grooming spot-check (round 302): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日第一次带猫去美容店。",
        "kind": "episodic",
        "cues": ["2026-01-10", "美容店"],
    },
    {
        "content": "2026年1月20日洗澡+剪指甲：套餐 150 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "套餐"],
    },
    {
        "content": "2026年2月1日猫毛打结，2 月 5 日剃毛。",
        "kind": "episodic",
        "cues": ["2026-02-01", "剃毛"],
    },
    {
        "content": "2026年2月5日剃毛完成。",
        "kind": "episodic",
        "cues": ["2026-02-05", "剃毛"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日美容。",
        "kind": "episodic",
        "cues": ["2026-03-01", "美容"],
    },
    {
        "content": "2026年3月15日美容完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "美容"],
    },
    {
        "content": "2026年4月1日猫耳螨，4 月 5 日治疗。",
        "kind": "episodic",
        "cues": ["2026-04-01", "耳螨"],
    },
    {
        "content": "2026年4月5日治疗完成。",
        "kind": "episodic",
        "cues": ["2026-04-05", "治疗"],
    },
    {
        "content": "2026年5月1日预约 5 月 10 日洗澡。",
        "kind": "episodic",
        "cues": ["2026-05-01", "洗澡"],
    },
    {
        "content": "2026年5月10日洗澡完成。",
        "kind": "episodic",
        "cues": ["2026-05-10", "洗澡"],
    },
    {
        "content": "2026年6月1日美容店涨价：套餐 180 元。",
        "kind": "episodic",
        "cues": ["2026-06-01", "涨价"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日美容。",
        "kind": "episodic",
        "cues": ["2026-06-15", "美容"],
    },
    {
        "content": "2026年6月25日美容完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "美容"],
    },
    {
        "content": "2026年7月1日猫应激，7 月 5 日恢复。",
        "kind": "episodic",
        "cues": ["2026-07-01", "应激"],
    },
    {
        "content": "2026年7月15日预约 8 月 10 日美容。",
        "kind": "episodic",
        "cues": ["2026-07-15", "美容"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日驱虫。",
        "kind": "episodic",
        "cues": ["2026-08-05", "驱虫"],
    },
    {
        "content": "美容店电话 400-666-1111。",
        "kind": "semantic",
        "cues": ["美容店", "电话"],
    },
    {
        "content": "美容店地址：宠物街 3 号。",
        "kind": "semantic",
        "cues": ["地址", "宠物街"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日美容店会员日。",
        "kind": "episodic",
        "cues": ["2026-08-08", "会员日"],
    },
]


QUESTIONS = [
    {
        "dim": "套餐价格",
        "q": "现在美容套餐多少钱？",
        "answer": "180元",
        "terms": ["180"],
    },
    {
        "dim": "剃毛记录",
        "q": "猫毛打结什么时候剃的？",
        "answer": "2月5日",
        "terms": ["5"],
    },
    {
        "dim": "耳螨治疗",
        "q": "猫耳螨什么时候治疗的？",
        "answer": "4月5日",
        "terms": ["5"],
    },
    {
        "dim": "未来安排",
        "q": "下次美容是什么时候？",
        "answer": "8月10日",
        "terms": ["10"],
    },
    {
        "dim": "应激恢复",
        "q": "猫应激什么时候恢复的？",
        "answer": "7月5日",
        "terms": ["5"],
    },
    {
        "dim": "驱虫提醒",
        "q": "什么时候驱虫？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "美容店信息",
        "q": "美容店在哪？电话多少？",
        "answer": "宠物街3号，400-666-1111",
        "terms": ["宠物街", "1111"],
    },
    {
        "dim": "会员日",
        "q": "美容店会员日什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "洗澡记录",
        "q": "上次洗澡是什么时候？",
        "answer": "5月10日",
        "terms": ["10"],
    },
    {
        "dim": "涨价记录",
        "q": "美容套餐什么时候涨价的？",
        "answer": "6月1日",
        "terms": ["1"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="宠物美容",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="groom_mem0db",
        out_name="groom_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
