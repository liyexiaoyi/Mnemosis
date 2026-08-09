"""Massage-physio spot-check (round 327): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日预约 1 月 20 日按摩。",
        "kind": "episodic",
        "cues": ["2026-01-10", "按摩"],
    },
    {
        "content": "2026年1月20日按摩完成。",
        "kind": "episodic",
        "cues": ["2026-01-20", "按摩"],
    },
    {
        "content": "2026年2月1日办按摩卡。",
        "kind": "episodic",
        "cues": ["2026-02-01", "按摩卡"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日理疗。",
        "kind": "episodic",
        "cues": ["2026-02-15", "理疗"],
    },
    {
        "content": "2026年2月25日理疗完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "理疗"],
    },
    {
        "content": "2026年3月1日按摩卡价格：120 元/次。",
        "kind": "semantic",
        "cues": ["按摩卡", "120"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日拔罐。",
        "kind": "episodic",
        "cues": ["2026-03-15", "拔罐"],
    },
    {
        "content": "2026年3月25日拔罐完成。",
        "kind": "episodic",
        "cues": ["2026-03-25", "拔罐"],
    },
    {
        "content": "2026年4月1日预约 4 月 15 日艾灸。",
        "kind": "episodic",
        "cues": ["2026-04-01", "艾灸"],
    },
    {
        "content": "2026年4月15日艾灸完成。",
        "kind": "episodic",
        "cues": ["2026-04-15", "艾灸"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日推拿。",
        "kind": "episodic",
        "cues": ["2026-05-01", "推拿"],
    },
    {
        "content": "2026年5月15日推拿完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "推拿"],
    },
    {
        "content": "2026年6月1日预约 6 月 15 日刮痧。",
        "kind": "episodic",
        "cues": ["2026-06-01", "刮痧"],
    },
    {
        "content": "2026年6月15日刮痧完成。",
        "kind": "episodic",
        "cues": ["2026-06-15", "刮痧"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日正骨。",
        "kind": "episodic",
        "cues": ["2026-07-01", "正骨"],
    },
    {
        "content": "2026年7月15日正骨完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "正骨"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日按摩。",
        "kind": "episodic",
        "cues": ["2026-08-01", "按摩"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日按摩卡到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "按摩卡"],
    },
    {
        "content": "理疗店电话 400-777-8888。",
        "kind": "semantic",
        "cues": ["理疗店", "电话"],
    },
    {
        "content": "按摩注意事项：饭后一小时。",
        "kind": "semantic",
        "cues": ["注意事项"],
    },
]


QUESTIONS = [
    {
        "dim": "首次按摩",
        "q": "第一次按摩是什么时候？",
        "answer": "1月20日",
        "terms": ["20"],
    },
    {
        "dim": "按摩卡",
        "q": "按摩卡多少钱一次？",
        "answer": "120元",
        "terms": ["120"],
    },
    {
        "dim": "理疗",
        "q": "理疗什么时候？",
        "answer": "2月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次按摩是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "拔罐",
        "q": "拔罐什么时候？",
        "answer": "3月25日",
        "terms": ["25"],
    },
    {
        "dim": "艾灸",
        "q": "艾灸什么时候？",
        "answer": "4月15日",
        "terms": ["15"],
    },
    {
        "dim": "刮痧",
        "q": "刮痧什么时候？",
        "answer": "6月15日",
        "terms": ["15"],
    },
    {
        "dim": "正骨",
        "q": "正骨什么时候？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "理疗店",
        "q": "理疗店电话多少？",
        "answer": "400-777-8888",
        "terms": ["8888"],
    },
    {
        "dim": "注意事项",
        "q": "按摩要注意什么？",
        "answer": "饭后一小时",
        "terms": ["饭后"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="按摩理疗",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="massage_mem0db",
        out_name="massage_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
