"""Flower-market spot-check (round 352): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月6日第一次在花卉市场买花，玫瑰一束120元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "玫瑰"],
    },
    {
        "content": "2026年1月12日收到第一束花配送。",
        "kind": "episodic",
        "cues": ["2026-01-12", "配送"],
    },
    {
        "content": "花卉市场营业时间：早7点到晚9点。",
        "kind": "semantic",
        "cues": ["营业时间", "7点"],
    },
    {
        "content": "花卉市场电话 0311-6666-2222。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "花材种类：玫瑰、百合、向日葵、满天星、绿萝。",
        "kind": "semantic",
        "cues": ["花材", "种类"],
    },
    {
        "content": "2026年2月2日预约2月14日情人节花束。",
        "kind": "episodic",
        "cues": ["2026-02-02", "情人节"],
    },
    {
        "content": "2026年2月14日情人节花束送达。",
        "kind": "episodic",
        "cues": ["2026-02-14", "情人节"],
    },
    {
        "content": "配送范围：市区三环内免费配送。",
        "kind": "semantic",
        "cues": ["配送", "范围"],
    },
    {
        "content": "2026年3月8日收到通知：3月22日会员日优惠。",
        "kind": "episodic",
        "cues": ["2026-03-08", "会员日"],
    },
    {
        "content": "2026年3月22日会员日购花8折。",
        "kind": "episodic",
        "cues": ["2026-03-22", "会员日"],
    },
    {
        "content": "保养说明：鲜花需每天换水，避免阳光直射。",
        "kind": "semantic",
        "cues": ["保养", "换水"],
    },
    {
        "content": "2026年4月10日购买百合两束，共180元。",
        "kind": "episodic",
        "cues": ["2026-04-10", "百合"],
    },
    {
        "content": "2026年4月15日收到百合配送。",
        "kind": "episodic",
        "cues": ["2026-04-15", "百合"],
    },
    {
        "content": "2026年5月6日收到通知：5月20日花卉展。",
        "kind": "episodic",
        "cues": ["2026-05-06", "花卉展"],
    },
    {
        "content": "2026年5月20日花卉展完成。",
        "kind": "episodic",
        "cues": ["2026-05-20", "花卉展"],
    },
    {
        "content": "2026年6月8日预约6月22日向日葵花束。",
        "kind": "episodic",
        "cues": ["2026-06-08", "向日葵"],
    },
    {
        "content": "2026年6月22日向日葵送达。",
        "kind": "episodic",
        "cues": ["2026-06-22", "向日葵"],
    },
    {
        "content": "2026年7月10日收到通知：7月26日插花课程。",
        "kind": "episodic",
        "cues": ["2026-07-10", "插花"],
    },
    {
        "content": "2026年8月4日预约8月18日下次配送。",
        "kind": "episodic",
        "cues": ["2026-08-04", "配送"],
    },
    {
        "content": "2026年8月10日收到提醒：8月26日会员卡积分清零。",
        "kind": "episodic",
        "cues": ["2026-08-10", "积分"],
    },
]


QUESTIONS = [
    {
        "dim": "首次购买",
        "q": "第一次在花卉市场买花是什么时候？",
        "answer": "1月6日",
        "terms": ["6"],
    },
    {
        "dim": "玫瑰价格",
        "q": "玫瑰一束多少钱？",
        "answer": "120元",
        "terms": ["120"],
    },
    {
        "dim": "下次配送",
        "q": "下次花束配送是什么时候？",
        "answer": "8月18日",
        "terms": ["18"],
    },
    {
        "dim": "营业时间",
        "q": "花卉市场几点开门？",
        "answer": "早7点",
        "terms": ["7"],
    },
    {
        "dim": "电话",
        "q": "花卉市场电话多少？",
        "answer": "0311-6666-2222",
        "terms": ["2222"],
    },
    {
        "dim": "花材种类",
        "q": "市场有哪些花材？",
        "answer": "玫瑰、百合、向日葵、满天星、绿萝",
        "terms": ["满天星"],
    },
    {
        "dim": "配送范围",
        "q": "配送范围是哪里？",
        "answer": "市区三环内免费",
        "terms": ["三环"],
    },
    {
        "dim": "会员日优惠",
        "q": "会员日购花打几折？",
        "answer": "8折",
        "terms": ["8"],
    },
    {
        "dim": "保养说明",
        "q": "鲜花怎么保养？",
        "answer": "每天换水，避免阳光直射",
        "terms": ["换水"],
    },
    {
        "dim": "积分清零",
        "q": "会员卡积分什么时候清零？",
        "answer": "8月26日",
        "terms": ["26"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="花卉市场",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="flower_mem0db",
        out_name="flower_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
