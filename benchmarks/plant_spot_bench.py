"""Houseplant-care spot-check (round 296): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买多肉：桃蛋、熊童子。",
        "kind": "episodic",
        "cues": ["2026-01-10", "多肉"],
    },
    {
        "content": "2026年1月20日买绿萝。",
        "kind": "episodic",
        "cues": ["2026-01-20", "绿萝"],
    },
    {
        "content": "2026年2月1日多肉换盆。",
        "kind": "episodic",
        "cues": ["2026-02-01", "换盆"],
    },
    {
        "content": "2026年2月15日绿萝长新叶。",
        "kind": "episodic",
        "cues": ["2026-02-15", "绿萝"],
    },
    {
        "content": "2026年3月1日多肉化水，3 月 5 日抢救。",
        "kind": "episodic",
        "cues": ["2026-03-01", "化水"],
    },
    {
        "content": "2026年3月5日抢救：控水。",
        "kind": "episodic",
        "cues": ["2026-03-05", "控水"],
    },
    {
        "content": "2026年4月1日买龟背竹。",
        "kind": "episodic",
        "cues": ["2026-04-01", "龟背竹"],
    },
    {
        "content": "2026年4月15日龟背竹开背。",
        "kind": "episodic",
        "cues": ["2026-04-15", "龟背竹"],
    },
    {
        "content": "2026年5月1日施肥：缓释肥。",
        "kind": "episodic",
        "cues": ["2026-05-01", "缓释肥"],
    },
    {
        "content": "2026年5月20日预约 6 月 1 日除虫。",
        "kind": "episodic",
        "cues": ["2026-05-20", "除虫"],
    },
    {
        "content": "2026年6月1日除虫完成。",
        "kind": "episodic",
        "cues": ["2026-06-01", "除虫"],
    },
    {
        "content": "2026年7月1日多肉度夏：遮阳。",
        "kind": "episodic",
        "cues": ["2026-07-01", "度夏"],
    },
    {
        "content": "2026年7月15日绿萝剪枝扦插。",
        "kind": "episodic",
        "cues": ["2026-07-15", "扦插"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日换大盆。",
        "kind": "episodic",
        "cues": ["2026-08-01", "换大盆"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日浇水。",
        "kind": "episodic",
        "cues": ["2026-08-05", "浇水"],
    },
    {
        "content": "植物店电话 400-111-9999。",
        "kind": "semantic",
        "cues": ["植物店", "电话"],
    },
    {
        "content": "浇水规则：多肉 10 天一次，绿萝 3 天一次。",
        "kind": "semantic",
        "cues": ["浇水规则"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日植物市集。",
        "kind": "episodic",
        "cues": ["2026-08-08", "市集"],
    },
]


QUESTIONS = [
    {
        "dim": "植物种类",
        "q": "买了什么多肉？",
        "answer": "桃蛋、熊童子",
        "terms": ["桃蛋"],
    },
    {
        "dim": "换盆记录",
        "q": "多肉什么时候换盆的？",
        "answer": "2月1日",
        "terms": ["1"],
    },
    {
        "dim": "病害处理",
        "q": "多肉化水什么时候抢救的？怎么救？",
        "answer": "3月5日，控水",
        "terms": ["控水"],
    },
    {
        "dim": "除虫记录",
        "q": "上次除虫是什么时候？",
        "answer": "6月1日",
        "terms": ["1"],
    },
    {
        "dim": "未来安排",
        "q": "下次换大盆是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "浇水规则",
        "q": "多肉多久浇一次水？",
        "answer": "10天一次",
        "terms": ["10"],
    },
    {
        "dim": "施肥记录",
        "q": "用什么肥料？",
        "answer": "缓释肥",
        "terms": ["缓释肥"],
    },
    {
        "dim": "扦插记录",
        "q": "绿萝什么时候剪枝扦插的？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "植物店",
        "q": "植物店电话多少？",
        "answer": "400-111-9999",
        "terms": ["9999"],
    },
    {
        "dim": "植物市集",
        "q": "植物市集什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="室内绿植",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="plant_mem0db",
        out_name="plant_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
