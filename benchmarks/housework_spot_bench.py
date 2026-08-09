"""Housekeeping-service spot-check (round 287): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日找家政：阿姨帮。",
        "kind": "episodic",
        "cues": ["2026-01-10", "家政"],
    },
    {
        "content": "2026年1月15日第一次保洁：2 小时，120 元。",
        "kind": "episodic",
        "cues": ["2026-01-15", "保洁"],
    },
    {
        "content": "2026年2月1日包月保洁：每周一次。",
        "kind": "semantic",
        "cues": ["包月", "每周"],
    },
    {
        "content": "2026年2月15日保洁阿姨换人：新阿姨小李。",
        "kind": "semantic",
        "cues": ["阿姨", "小李"],
    },
    {
        "content": "2026年3月1日预约 3 月 10 日深度保洁。",
        "kind": "episodic",
        "cues": ["2026-03-01", "深度保洁"],
    },
    {
        "content": "2026年3月10日深度保洁完成。",
        "kind": "episodic",
        "cues": ["2026-03-10", "深度保洁"],
    },
    {
        "content": "2026年4月1日买清洁剂：抽油烟机专用。",
        "kind": "episodic",
        "cues": ["2026-04-01", "清洁剂"],
    },
    {
        "content": "2026年4月15日阿姨说玻璃擦不干净，换工具。",
        "kind": "episodic",
        "cues": ["2026-04-15", "玻璃"],
    },
    {
        "content": "2026年5月1日预约 5 月 10 日擦玻璃。",
        "kind": "episodic",
        "cues": ["2026-05-01", "擦玻璃"],
    },
    {
        "content": "2026年5月10日擦玻璃完成。",
        "kind": "episodic",
        "cues": ["2026-05-10", "擦玻璃"],
    },
    {
        "content": "2026年6月1日家政涨价：每小时 70 元。",
        "kind": "episodic",
        "cues": ["2026-06-01", "涨价"],
    },
    {
        "content": "2026年6月15日包月费用 280 元。",
        "kind": "episodic",
        "cues": ["2026-06-15", "包月"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日除螨。",
        "kind": "episodic",
        "cues": ["2026-07-01", "除螨"],
    },
    {
        "content": "2026年7月10日除螨保洁完成。",
        "kind": "episodic",
        "cues": ["2026-07-10", "除螨"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日大扫除。",
        "kind": "episodic",
        "cues": ["2026-08-01", "大扫除"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日前续包月。",
        "kind": "episodic",
        "cues": ["2026-08-05", "续费"],
    },
    {
        "content": "家政客服 400-333-4444。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "保洁用品：自带鞋套。",
        "kind": "semantic",
        "cues": ["鞋套"],
    },
    {
        "content": "2026年8月8日阿姨请假：8 月 20 日换班。",
        "kind": "episodic",
        "cues": ["2026-08-08", "换班"],
    },
    {
        "content": "家政合同：一年一签。",
        "kind": "semantic",
        "cues": ["合同"],
    },
]


QUESTIONS = [
    {
        "dim": "服务记录",
        "q": "上次保洁是什么时候？做了什么？",
        "answer": "7月10日，除螨",
        "terms": ["除螨"],
    },
    {
        "dim": "未来安排",
        "q": "下次大扫除是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "服务费用",
        "q": "现在保洁每小时多少钱？",
        "answer": "70元",
        "terms": ["70"],
    },
    {
        "dim": "包月服务",
        "q": "包月保洁多少钱？多久一次？",
        "answer": "280元，每周一次",
        "terms": ["280", "每周"],
    },
    {
        "dim": "阿姨信息",
        "q": "现在保洁阿姨是谁？",
        "answer": "小李",
        "terms": ["小李"],
    },
    {
        "dim": "续费提醒",
        "q": "包月什么时候续？",
        "answer": "8月15日前",
        "terms": ["15"],
    },
    {
        "dim": "客服电话",
        "q": "家政客服电话多少？",
        "answer": "400-333-4444",
        "terms": ["4444"],
    },
    {
        "dim": "换班安排",
        "q": "阿姨什么时候请假换班？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "清洁用品",
        "q": "买了什么清洁剂？",
        "answer": "抽油烟机专用",
        "terms": ["抽油烟机"],
    },
    {
        "dim": "合同期限",
        "q": "家政合同多久一签？",
        "answer": "一年",
        "terms": ["一年"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家政保洁",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="housework_mem0db",
        out_name="housework_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
