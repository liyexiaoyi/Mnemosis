"""Second-hand trading spot-check (round 314): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日在闲鱼挂闲置。",
        "kind": "episodic",
        "cues": ["2026-01-10", "闲鱼"],
    },
    {
        "content": "2026年1月20日卖出旧手机：1500 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "旧手机"],
    },
    {
        "content": "2026年2月1日预约 2 月 15 日面交。",
        "kind": "episodic",
        "cues": ["2026-02-01", "面交"],
    },
    {
        "content": "2026年2月15日面交完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "面交"],
    },
    {
        "content": "2026年3月1日买二手自行车：600 元。",
        "kind": "episodic",
        "cues": ["2026-03-01", "自行车"],
    },
    {
        "content": "2026年3月15日自行车变速有问题，3 月 20 日修。",
        "kind": "episodic",
        "cues": ["2026-03-15", "变速"],
    },
    {
        "content": "2026年3月20日修好。",
        "kind": "episodic",
        "cues": ["2026-03-20", "变速"],
    },
    {
        "content": "2026年4月1日挂卖旧书。",
        "kind": "episodic",
        "cues": ["2026-04-01", "旧书"],
    },
    {
        "content": "2026年4月15日旧书卖出 80 元。",
        "kind": "episodic",
        "cues": ["2026-04-15", "旧书"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日收闲置。",
        "kind": "episodic",
        "cues": ["2026-05-01", "闲置"],
    },
    {
        "content": "2026年5月15日收闲置完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "闲置"],
    },
    {
        "content": "2026年6月1日买二手音箱。",
        "kind": "episodic",
        "cues": ["2026-06-01", "音箱"],
    },
    {
        "content": "2026年6月15日音箱音质检查。",
        "kind": "episodic",
        "cues": ["2026-06-15", "音质"],
    },
    {
        "content": "2026年7月1日挂卖旧相机。",
        "kind": "episodic",
        "cues": ["2026-07-01", "相机"],
    },
    {
        "content": "2026年7月15日相机降价：从 3000 降到 2600。",
        "kind": "episodic",
        "cues": ["2026-07-15", "相机"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日面交相机。",
        "kind": "episodic",
        "cues": ["2026-08-01", "相机"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日确认收货。",
        "kind": "episodic",
        "cues": ["2026-08-05", "确认收货"],
    },
    {
        "content": "二手平台客服 400-111-7777。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "交易规则：面交验货。",
        "kind": "semantic",
        "cues": ["交易规则"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日二手市集。",
        "kind": "episodic",
        "cues": ["2026-08-08", "市集"],
    },
]


QUESTIONS = [
    {
        "dim": "卖出记录",
        "q": "旧手机卖了多少钱？",
        "answer": "1500元",
        "terms": ["1500"],
    },
    {
        "dim": "自行车",
        "q": "自行车多少钱？有什么问题？",
        "answer": "600元，变速有问题",
        "terms": ["变速"],
    },
    {
        "dim": "旧书卖出",
        "q": "旧书卖了多少钱？",
        "answer": "80元",
        "terms": ["80"],
    },
    {
        "dim": "未来安排",
        "q": "下次面交相机是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "相机价格",
        "q": "相机现在挂多少？",
        "answer": "2600元",
        "terms": ["2600"],
    },
    {
        "dim": "音箱检查",
        "q": "音箱买了以后检查什么？",
        "answer": "音质",
        "terms": ["音质"],
    },
    {
        "dim": "平台客服",
        "q": "二手平台客服电话多少？",
        "answer": "400-111-7777",
        "terms": ["7777"],
    },
    {
        "dim": "交易规则",
        "q": "交易规则是什么？",
        "answer": "面交验货",
        "terms": ["验货"],
    },
    {
        "dim": "确认收货",
        "q": "什么时候确认收货？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "二手市集",
        "q": "二手市集什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="二手交易",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="secondhand_mem0db",
        out_name="secondhand_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
