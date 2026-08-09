"""Furniture-installation spot-check (round 313): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日买书桌：宜家 899 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "书桌"],
    },
    {
        "content": "2026年1月20日预约 1 月 30 日安装。",
        "kind": "episodic",
        "cues": ["2026-01-20", "安装"],
    },
    {
        "content": "2026年1月30日书桌安装完成。",
        "kind": "episodic",
        "cues": ["2026-01-30", "书桌"],
    },
    {
        "content": "2026年2月1日买衣柜：定制。",
        "kind": "episodic",
        "cues": ["2026-02-01", "衣柜"],
    },
    {
        "content": "2026年2月15日衣柜量尺：2 月 25 日。",
        "kind": "episodic",
        "cues": ["2026-02-15", "量尺"],
    },
    {
        "content": "2026年2月25日量尺完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "量尺"],
    },
    {
        "content": "2026年3月1日预约 3 月 20 日衣柜安装。",
        "kind": "episodic",
        "cues": ["2026-03-01", "衣柜"],
    },
    {
        "content": "2026年3月20日衣柜安装完成。",
        "kind": "episodic",
        "cues": ["2026-03-20", "衣柜"],
    },
    {
        "content": "2026年4月1日买床垫：弹簧床垫。",
        "kind": "episodic",
        "cues": ["2026-04-01", "床垫"],
    },
    {
        "content": "2026年4月15日床垫到货。",
        "kind": "episodic",
        "cues": ["2026-04-15", "床垫"],
    },
    {
        "content": "2026年5月1日买沙发：布艺沙发。",
        "kind": "episodic",
        "cues": ["2026-05-01", "沙发"],
    },
    {
        "content": "2026年5月15日预约 5 月 25 日沙发安装。",
        "kind": "episodic",
        "cues": ["2026-05-15", "沙发"],
    },
    {
        "content": "2026年5月25日沙发安装完成。",
        "kind": "episodic",
        "cues": ["2026-05-25", "沙发"],
    },
    {
        "content": "2026年6月1日书桌螺丝松，6 月 5 日加固。",
        "kind": "episodic",
        "cues": ["2026-06-01", "加固"],
    },
    {
        "content": "2026年6月5日加固完成。",
        "kind": "episodic",
        "cues": ["2026-06-05", "加固"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日柜门调整。",
        "kind": "episodic",
        "cues": ["2026-07-01", "柜门"],
    },
    {
        "content": "2026年7月15日调整完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "柜门"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日买餐椅。",
        "kind": "episodic",
        "cues": ["2026-08-01", "餐椅"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日书桌保修。",
        "kind": "episodic",
        "cues": ["2026-08-05", "保修"],
    },
    {
        "content": "安装师傅电话 400-333-1111。",
        "kind": "semantic",
        "cues": ["安装", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "书桌价格",
        "q": "书桌多少钱？",
        "answer": "899元",
        "terms": ["899"],
    },
    {
        "dim": "衣柜量尺",
        "q": "衣柜什么时候量尺的？",
        "answer": "2月25日",
        "terms": ["25"],
    },
    {
        "dim": "沙发安装",
        "q": "沙发什么时候安装的？",
        "answer": "5月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次买餐椅是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "床垫类型",
        "q": "床垫是什么类型？",
        "answer": "弹簧床垫",
        "terms": ["弹簧"],
    },
    {
        "dim": "书桌加固",
        "q": "书桌螺丝什么时候加固的？",
        "answer": "6月5日",
        "terms": ["5"],
    },
    {
        "dim": "柜门调整",
        "q": "柜门什么时候调整的？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "安装师傅",
        "q": "安装师傅电话多少？",
        "answer": "400-333-1111",
        "terms": ["1111"],
    },
    {
        "dim": "书桌保修",
        "q": "书桌保修什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "衣柜定制",
        "q": "衣柜是什么？",
        "answer": "定制",
        "terms": ["定制"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家具安装",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="furniture_mem0db",
        out_name="furniture_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
