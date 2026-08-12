"""Hotel-membership spot-check (round 328): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日办酒店会员卡。",
        "kind": "episodic",
        "cues": ["2026-01-10", "会员卡"],
    },
    {
        "content": "2026年1月20日第一次入住：标准间。",
        "kind": "episodic",
        "cues": ["2026-01-20", "入住"],
    },
    {
        "content": "2026年2月1日会员积分 2000 分。",
        "kind": "episodic",
        "cues": ["2026-02-01", "积分"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日入住。",
        "kind": "episodic",
        "cues": ["2026-02-15", "入住"],
    },
    {
        "content": "2026年2月25日入住完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "入住"],
    },
    {
        "content": "2026年3月1日会员价：9 折。",
        "kind": "semantic",
        "cues": ["会员价", "9折"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日早餐。",
        "kind": "episodic",
        "cues": ["2026-03-15", "早餐"],
    },
    {
        "content": "2026年3月25日早餐升级。",
        "kind": "episodic",
        "cues": ["2026-03-25", "早餐"],
    },
    {
        "content": "2026年4月1日积分兑换：1000 分换一晚。",
        "kind": "semantic",
        "cues": ["积分", "1000"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日入住。",
        "kind": "episodic",
        "cues": ["2026-04-15", "入住"],
    },
    {
        "content": "2026年4月25日入住完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "入住"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日延迟退房。",
        "kind": "episodic",
        "cues": ["2026-05-01", "延迟退房"],
    },
    {
        "content": "2026年5月15日延迟退房完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "延迟退房"],
    },
    {
        "content": "2026年6月1日会员过期：6 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-06-01", "过期"],
    },
    {
        "content": "2026年6月20日续会员。",
        "kind": "episodic",
        "cues": ["2026-06-20", "续费"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日入住。",
        "kind": "episodic",
        "cues": ["2026-07-01", "入住"],
    },
    {
        "content": "2026年7月15日入住完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "入住"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日入住。",
        "kind": "episodic",
        "cues": ["2026-08-01", "入住"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日积分清零。",
        "kind": "episodic",
        "cues": ["2026-08-05", "积分"],
    },
    {
        "content": "酒店客服 400-666-3333。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "首次入住",
        "q": "第一次入住是什么时候？",
        "answer": "1月20日",
        "terms": ["20"],
    },
    {
        "dim": "会员积分",
        "q": "积分记录是多少？",
        "answer": "2000分",
        "terms": ["2000"],
    },
    {
        "dim": "会员价",
        "q": "会员价几折？",
        "answer": "9折",
        "terms": ["9"],
    },
    {
        "dim": "未来安排",
        "q": "下次入住是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "积分兑换",
        "q": "多少分换一晚？",
        "answer": "1000分",
        "terms": ["1000"],
    },
    {
        "dim": "延迟退房",
        "q": "延迟退房什么时候？",
        "answer": "5月15日",
        "terms": ["15"],
    },
    {
        "dim": "续会员",
        "q": "会员什么时候续的？",
        "answer": "6月20日",
        "terms": ["20"],
    },
    {
        "dim": "酒店客服",
        "q": "酒店客服电话多少？",
        "answer": "400-666-3333",
        "terms": ["3333"],
    },
    {
        "dim": "积分清零",
        "q": "积分什么时候清零？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "早餐升级",
        "q": "早餐什么时候升级？",
        "answer": "3月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="酒店会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="hotel_mem0db",
        out_name="hotel_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
