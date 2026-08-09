"""Baking spot-check (round 309): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日第一次做蛋糕。",
        "kind": "episodic",
        "cues": ["2026-01-10", "蛋糕"],
    },
    {
        "content": "2026年1月20日买烤箱烤盘。",
        "kind": "episodic",
        "cues": ["2026-01-20", "烤箱"],
    },
    {
        "content": "2026年2月1日做曲奇：黄油曲奇。",
        "kind": "episodic",
        "cues": ["2026-02-01", "曲奇"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日烘焙课。",
        "kind": "episodic",
        "cues": ["2026-02-15", "烘焙课"],
    },
    {
        "content": "2026年2月25日烘焙课完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "烘焙课"],
    },
    {
        "content": "2026年3月1日做面包：全麦吐司。",
        "kind": "episodic",
        "cues": ["2026-03-01", "吐司"],
    },
    {
        "content": "2026年3月15日买厨师机。",
        "kind": "episodic",
        "cues": ["2026-03-15", "厨师机"],
    },
    {
        "content": "2026年4月1日做提拉米苏。",
        "kind": "episodic",
        "cues": ["2026-04-01", "提拉米苏"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日蛋糕装饰课。",
        "kind": "episodic",
        "cues": ["2026-04-15", "装饰课"],
    },
    {
        "content": "2026年4月25日装饰课完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "装饰课"],
    },
    {
        "content": "2026年5月1日做生日蛋糕。",
        "kind": "episodic",
        "cues": ["2026-05-01", "生日蛋糕"],
    },
    {
        "content": "2026年5月20日预约 6 月 1 日法式甜点课。",
        "kind": "episodic",
        "cues": ["2026-05-20", "甜点课"],
    },
    {
        "content": "2026年6月1日甜点课完成。",
        "kind": "episodic",
        "cues": ["2026-06-01", "甜点课"],
    },
    {
        "content": "2026年7月1日做马卡龙失败。",
        "kind": "episodic",
        "cues": ["2026-07-01", "马卡龙"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日马卡龙课。",
        "kind": "episodic",
        "cues": ["2026-07-15", "马卡龙"],
    },
    {
        "content": "2026年7月25日马卡龙课完成。",
        "kind": "episodic",
        "cues": ["2026-07-25", "马卡龙"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日做月饼。",
        "kind": "episodic",
        "cues": ["2026-08-01", "月饼"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日买淡奶油。",
        "kind": "episodic",
        "cues": ["2026-08-05", "淡奶油"],
    },
    {
        "content": "烘焙店电话 400-222-8888。",
        "kind": "semantic",
        "cues": ["烘焙店", "电话"],
    },
    {
        "content": "烤箱温度：上下火 170 度。",
        "kind": "semantic",
        "cues": ["烤箱", "温度"],
    },
]


QUESTIONS = [
    {
        "dim": "甜点记录",
        "q": "做过什么甜点？",
        "answer": "马卡龙",
        "terms": ["马卡龙"],
    },
    {
        "dim": "烘焙课",
        "q": "烘焙课什么时候上的？",
        "answer": "2月25日",
        "terms": ["25"],
    },
    {
        "dim": "马卡龙",
        "q": "马卡龙第一次自己做是什么时候？结果如何？",
        "answer": "7月1日，失败",
        "terms": ["失败"],
    },
    {
        "dim": "未来安排",
        "q": "下次做月饼是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "烘焙设备",
        "q": "买了什么设备？",
        "answer": "厨师机",
        "terms": ["厨师机"],
    },
    {
        "dim": "装饰课",
        "q": "蛋糕装饰课什么时候？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "烤箱温度",
        "q": "烤箱多少度？",
        "answer": "170度",
        "terms": ["170"],
    },
    {
        "dim": "烘焙店",
        "q": "烘焙店电话多少？",
        "answer": "400-222-8888",
        "terms": ["8888"],
    },
    {
        "dim": "淡奶油",
        "q": "什么时候买淡奶油？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "生日蛋糕",
        "q": "生日蛋糕什么时候做的？",
        "answer": "5月1日",
        "terms": ["1"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="烘焙学习",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="baking_mem0db",
        out_name="baking_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
