"""Laundry-service spot-check (round 329): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日第一次去干洗店。",
        "kind": "episodic",
        "cues": ["2026-01-10", "干洗店"],
    },
    {
        "content": "2026年1月20日干洗羽绒服：80 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "羽绒服"],
    },
    {
        "content": "2026年2月1日办洗衣卡：充 500 送 50。",
        "kind": "episodic",
        "cues": ["2026-02-01", "洗衣卡"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日洗窗帘。",
        "kind": "episodic",
        "cues": ["2026-02-15", "窗帘"],
    },
    {
        "content": "2026年2月25日窗帘洗好。",
        "kind": "episodic",
        "cues": ["2026-02-25", "窗帘"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日洗被套。",
        "kind": "episodic",
        "cues": ["2026-03-01", "被套"],
    },
    {
        "content": "2026年3月15日被套洗好。",
        "kind": "episodic",
        "cues": ["2026-03-15", "被套"],
    },
    {
        "content": "2026年4月1日羽绒服有异味，4 月 5 日返洗。",
        "kind": "episodic",
        "cues": ["2026-04-01", "返洗"],
    },
    {
        "content": "2026年4月5日返洗完成。",
        "kind": "episodic",
        "cues": ["2026-04-05", "返洗"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日洗西装。",
        "kind": "episodic",
        "cues": ["2026-05-01", "西装"],
    },
    {
        "content": "2026年5月15日西装洗好。",
        "kind": "episodic",
        "cues": ["2026-05-15", "西装"],
    },
    {
        "content": "2026年6月1日洗衣卡余额：350 元。",
        "kind": "semantic",
        "cues": ["洗衣卡", "350"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日洗地毯。",
        "kind": "episodic",
        "cues": ["2026-06-15", "地毯"],
    },
    {
        "content": "2026年6月25日地毯洗好。",
        "kind": "episodic",
        "cues": ["2026-06-25", "地毯"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日洗玩偶。",
        "kind": "episodic",
        "cues": ["2026-07-01", "玩偶"],
    },
    {
        "content": "2026年7月15日玩偶洗好。",
        "kind": "episodic",
        "cues": ["2026-07-15", "玩偶"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日洗冬衣。",
        "kind": "episodic",
        "cues": ["2026-08-01", "冬衣"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日洗衣卡到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "洗衣卡"],
    },
    {
        "content": "干洗店电话 400-111-2222。",
        "kind": "semantic",
        "cues": ["干洗店", "电话"],
    },
    {
        "content": "取件时间：3 天后。",
        "kind": "semantic",
        "cues": ["取件时间"],
    },
]


QUESTIONS = [
    {
        "dim": "干洗价格",
        "q": "干洗羽绒服多少钱？",
        "answer": "80元",
        "terms": ["80"],
    },
    {
        "dim": "洗衣卡",
        "q": "洗衣卡充多少送多少？",
        "answer": "充500送50",
        "terms": ["500", "50"],
    },
    {
        "dim": "窗帘",
        "q": "窗帘什么时候洗好的？",
        "answer": "2月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次洗冬衣是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "返洗",
        "q": "羽绒服返洗什么时候？",
        "answer": "4月5日",
        "terms": ["5"],
    },
    {
        "dim": "西装",
        "q": "西装什么时候洗好的？",
        "answer": "5月15日",
        "terms": ["15"],
    },
    {
        "dim": "洗衣卡余额",
        "q": "洗衣卡余额多少？",
        "answer": "350元",
        "terms": ["350"],
    },
    {
        "dim": "地毯",
        "q": "地毯什么时候洗好的？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "干洗店",
        "q": "干洗店电话多少？",
        "answer": "400-111-2222",
        "terms": ["2222"],
    },
    {
        "dim": "取件时间",
        "q": "取件要几天？",
        "answer": "3天",
        "terms": ["3"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="洗衣店服务",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="laundry_mem0db",
        out_name="laundry_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
