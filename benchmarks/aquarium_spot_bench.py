"""Aquarium spot-check (round 295): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日买鱼缸：60cm，400 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "鱼缸"],
    },
    {
        "content": "2026年1月20日开缸养水。",
        "kind": "episodic",
        "cues": ["2026-01-20", "养水"],
    },
    {
        "content": "2026年2月1日买鱼：孔雀鱼 8 条。",
        "kind": "episodic",
        "cues": ["2026-02-01", "孔雀鱼"],
    },
    {
        "content": "2026年2月15日孔雀鱼生小鱼。",
        "kind": "episodic",
        "cues": ["2026-02-15", "孔雀鱼"],
    },
    {
        "content": "2026年3月1日买过滤器：外置桶。",
        "kind": "episodic",
        "cues": ["2026-03-01", "过滤器"],
    },
    {
        "content": "2026年3月15日鱼缸爆藻，3 月 20 日清理。",
        "kind": "episodic",
        "cues": ["2026-03-15", "爆藻"],
    },
    {
        "content": "2026年3月20日清藻完成。",
        "kind": "episodic",
        "cues": ["2026-03-20", "清藻"],
    },
    {
        "content": "2026年4月1日买加热棒：200W。",
        "kind": "episodic",
        "cues": ["2026-04-01", "加热棒"],
    },
    {
        "content": "2026年4月15日换水：每周四。",
        "kind": "semantic",
        "cues": ["换水", "周四"],
    },
    {
        "content": "2026年5月1日买水草：水榕。",
        "kind": "episodic",
        "cues": ["2026-05-01", "水草"],
    },
    {
        "content": "2026年5月20日预约 5 月 30 日鱼缸维护。",
        "kind": "episodic",
        "cues": ["2026-05-20", "维护"],
    },
    {
        "content": "2026年5月30日维护完成。",
        "kind": "episodic",
        "cues": ["2026-05-30", "维护"],
    },
    {
        "content": "2026年6月1日鱼食：薄片 45 元。",
        "kind": "episodic",
        "cues": ["2026-06-01", "鱼食"],
    },
    {
        "content": "2026年6月15日孔雀鱼又生一窝。",
        "kind": "episodic",
        "cues": ["2026-06-15", "孔雀鱼"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日清洗滤桶。",
        "kind": "episodic",
        "cues": ["2026-07-01", "滤桶"],
    },
    {
        "content": "2026年7月10日清洗滤桶完成。",
        "kind": "episodic",
        "cues": ["2026-07-10", "滤桶"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日买新鱼。",
        "kind": "episodic",
        "cues": ["2026-08-01", "买鱼"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日换水。",
        "kind": "episodic",
        "cues": ["2026-08-05", "换水"],
    },
    {
        "content": "水族店电话 400-222-3333。",
        "kind": "semantic",
        "cues": ["水族店", "电话"],
    },
    {
        "content": "水质测试：每周一次。",
        "kind": "semantic",
        "cues": ["水质测试"],
    },
]


QUESTIONS = [
    {
        "dim": "鱼缸信息",
        "q": "鱼缸多大？多少钱？",
        "answer": "60cm，400元",
        "terms": ["400"],
    },
    {
        "dim": "养鱼记录",
        "q": "养了什么鱼？",
        "answer": "孔雀鱼",
        "terms": ["孔雀鱼"],
    },
    {
        "dim": "繁殖记录",
        "q": "孔雀鱼最近一次生小鱼是什么时候？",
        "answer": "6月15日",
        "terms": ["15"],
    },
    {
        "dim": "换水规则",
        "q": "多久换一次水？",
        "answer": "每周四",
        "terms": ["周四"],
    },
    {
        "dim": "未来安排",
        "q": "下次买新鱼是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "清藻记录",
        "q": "鱼缸爆藻什么时候清理的？",
        "answer": "3月20日",
        "terms": ["20"],
    },
    {
        "dim": "过滤设备",
        "q": "过滤器是什么类型？",
        "answer": "外置桶",
        "terms": ["外置桶"],
    },
    {
        "dim": "鱼食费用",
        "q": "鱼食多少钱？",
        "answer": "45元",
        "terms": ["45"],
    },
    {
        "dim": "滤桶维护",
        "q": "上次清洗滤桶是什么时候？",
        "answer": "7月10日",
        "terms": ["10"],
    },
    {
        "dim": "水质测试",
        "q": "水质测试多久一次？",
        "answer": "每周一次",
        "terms": ["每周"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="水族养鱼",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="aquarium_mem0db",
        out_name="aquarium_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
