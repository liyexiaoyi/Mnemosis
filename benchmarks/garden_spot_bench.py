"""Balcony-gardening spot-check (round 284): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年2月1日买花盆 10 个，营养土 2 袋。",
        "kind": "episodic",
        "cues": ["2026-02-01", "花盆"],
    },
    {
        "content": "2026年2月10日播种：番茄、辣椒、薄荷。",
        "kind": "episodic",
        "cues": ["2026-02-10", "播种"],
    },
    {
        "content": "2026年3月5日发芽：番茄 8 棵。",
        "kind": "episodic",
        "cues": ["2026-03-05", "发芽"],
    },
    {
        "content": "2026年3月20日移栽到阳台。",
        "kind": "episodic",
        "cues": ["2026-03-20", "移栽"],
    },
    {
        "content": "2026年4月1日买肥料：复合肥。",
        "kind": "episodic",
        "cues": ["2026-04-01", "肥料"],
    },
    {
        "content": "2026年4月15日辣椒开花。",
        "kind": "episodic",
        "cues": ["2026-04-15", "辣椒"],
    },
    {
        "content": "2026年5月1日番茄结果 12 个。",
        "kind": "episodic",
        "cues": ["2026-05-01", "番茄"],
    },
    {
        "content": "2026年5月20日薄荷疯长，剪枝。",
        "kind": "episodic",
        "cues": ["2026-05-20", "薄荷"],
    },
    {
        "content": "2026年6月1日番茄红了 5 个，第一次采摘。",
        "kind": "episodic",
        "cues": ["2026-06-01", "采摘"],
    },
    {
        "content": "2026年6月15日辣椒收 6 个。",
        "kind": "episodic",
        "cues": ["2026-06-15", "辣椒"],
    },
    {
        "content": "2026年7月1日天热，每天浇水。",
        "kind": "episodic",
        "cues": ["2026-07-01", "浇水"],
    },
    {
        "content": "2026年7月10日番茄叶发黄，7 月 15 日补铁。",
        "kind": "episodic",
        "cues": ["2026-07-10", "补铁"],
    },
    {
        "content": "2026年7月15日补铁后好转。",
        "kind": "episodic",
        "cues": ["2026-07-15", "补铁"],
    },
    {
        "content": "2026年8月1日预约 8 月 10 日买秋播种子。",
        "kind": "episodic",
        "cues": ["2026-08-01", "种子"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日前修剪。",
        "kind": "episodic",
        "cues": ["2026-08-05", "修剪"],
    },
    {
        "content": "阳台日照：南阳台，上午 6 小时。",
        "kind": "semantic",
        "cues": ["日照"],
    },
    {
        "content": "浇水规则：夏天每天，冬天 3 天一次。",
        "kind": "semantic",
        "cues": ["浇水"],
    },
    {
        "content": "施肥：每月一次复合肥。",
        "kind": "semantic",
        "cues": ["施肥"],
    },
    {
        "content": "虫害：蚜虫用肥皂水。",
        "kind": "semantic",
        "cues": ["蚜虫"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日社区园艺课。",
        "kind": "episodic",
        "cues": ["2026-08-08", "园艺课"],
    },
    {
        "content": "花盆位置：番茄在左，辣椒在右。",
        "kind": "semantic",
        "cues": ["位置"],
    },
    {
        "content": "2026年8月9日预约 8 月 18 日换大盆。",
        "kind": "episodic",
        "cues": ["2026-08-09", "换盆"],
    },
    {
        "content": "土壤：通用营养土混珍珠岩。",
        "kind": "semantic",
        "cues": ["土壤"],
    },
    {
        "content": "薄荷用途：泡茶。",
        "kind": "semantic",
        "cues": ["薄荷"],
    },
]


QUESTIONS = [
    {
        "dim": "采摘记录",
        "q": "上次采摘是什么时候？摘了什么？",
        "answer": "6月15日，辣椒6个",
        "terms": ["辣椒"],
    },
    {
        "dim": "未来安排",
        "q": "下次换大盆是什么时候？",
        "answer": "8月18日",
        "terms": ["18"],
    },
    {
        "dim": "虫害处理",
        "q": "蚜虫怎么处理？",
        "answer": "肥皂水",
        "terms": ["肥皂水"],
    },
    {
        "dim": "浇水规则",
        "q": "夏天多久浇一次水？",
        "answer": "每天",
        "terms": ["每天"],
    },
    {
        "dim": "施肥规则",
        "q": "多久施一次肥？",
        "answer": "每月一次",
        "terms": ["每月"],
    },
    {
        "dim": "番茄问题",
        "q": "番茄叶发黄怎么解决的？",
        "answer": "补铁",
        "terms": ["补铁"],
    },
    {
        "dim": "花盆位置",
        "q": "番茄种在哪边？",
        "answer": "左边",
        "terms": ["左"],
    },
    {
        "dim": "园艺课程",
        "q": "社区园艺课什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "土壤配方",
        "q": "土壤怎么配？",
        "answer": "营养土混珍珠岩",
        "terms": ["珍珠岩"],
    },
    {
        "dim": "薄荷用途",
        "q": "薄荷用来干什么？",
        "answer": "泡茶",
        "terms": ["泡茶"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="阳台园艺",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="garden_mem0db",
        out_name="garden_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
