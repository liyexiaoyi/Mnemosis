"""Children-eye-care spot-check (round 316): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日孩子视力筛查：4.9。",
        "kind": "episodic",
        "cues": ["2026-01-10", "筛查"],
    },
    {
        "content": "2026年1月20日预约 1 月 30 日散瞳验光。",
        "kind": "episodic",
        "cues": ["2026-01-20", "验光"],
    },
    {
        "content": "2026年1月30日验光完成。",
        "kind": "episodic",
        "cues": ["2026-01-30", "验光"],
    },
    {
        "content": "2026年2月1日配眼镜：防控镜片。",
        "kind": "episodic",
        "cues": ["2026-02-01", "防控镜片"],
    },
    {
        "content": "2026年2月15日取眼镜。",
        "kind": "episodic",
        "cues": ["2026-02-15", "取镜"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日复查。",
        "kind": "episodic",
        "cues": ["2026-03-01", "复查"],
    },
    {
        "content": "2026年3月15日复查：度数没涨。",
        "kind": "episodic",
        "cues": ["2026-03-15", "复查"],
    },
    {
        "content": "2026年4月1日买护眼台灯。",
        "kind": "episodic",
        "cues": ["2026-04-01", "台灯"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日视力训练。",
        "kind": "episodic",
        "cues": ["2026-04-15", "训练"],
    },
    {
        "content": "2026年4月25日视力训练开始。",
        "kind": "episodic",
        "cues": ["2026-04-25", "训练"],
    },
    {
        "content": "2026年5月1日预约 5 月 20 日复查。",
        "kind": "episodic",
        "cues": ["2026-05-01", "复查"],
    },
    {
        "content": "2026年5月20日复查：右眼 5.0。",
        "kind": "episodic",
        "cues": ["2026-05-20", "复查"],
    },
    {
        "content": "2026年6月1日买叶黄素。",
        "kind": "episodic",
        "cues": ["2026-06-01", "叶黄素"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日换镜片。",
        "kind": "episodic",
        "cues": ["2026-06-15", "换镜片"],
    },
    {
        "content": "2026年6月25日换镜片完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "换镜片"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日视力训练。",
        "kind": "episodic",
        "cues": ["2026-07-01", "训练"],
    },
    {
        "content": "2026年7月15日视力训练完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "训练"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日复查。",
        "kind": "episodic",
        "cues": ["2026-08-01", "复查"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日滴眼药水。",
        "kind": "episodic",
        "cues": ["2026-08-05", "眼药水"],
    },
    {
        "content": "眼科电话 400-777-3333。",
        "kind": "semantic",
        "cues": ["眼科", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "视力筛查",
        "q": "视力筛查多少？",
        "answer": "4.9",
        "terms": ["4.9"],
    },
    {
        "dim": "眼镜配置",
        "q": "配了什么镜片？",
        "answer": "防控镜片",
        "terms": ["防控"],
    },
    {
        "dim": "复查记录",
        "q": "上次复查是什么时候？右眼多少？",
        "answer": "5月20日，5.0",
        "terms": ["5.0"],
    },
    {
        "dim": "未来安排",
        "q": "下次复查是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "护眼设备",
        "q": "买了什么护眼设备？",
        "answer": "护眼台灯",
        "terms": ["台灯"],
    },
    {
        "dim": "营养补充",
        "q": "买了什么营养素？",
        "answer": "叶黄素",
        "terms": ["叶黄素"],
    },
    {
        "dim": "换镜片",
        "q": "镜片什么时候换的？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "视力训练",
        "q": "上次视力训练是什么时候？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "眼科电话",
        "q": "眼科电话多少？",
        "answer": "400-777-3333",
        "terms": ["3333"],
    },
    {
        "dim": "眼药水",
        "q": "什么时候滴眼药水？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="儿童护眼",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="eye_mem0db",
        out_name="eye_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
