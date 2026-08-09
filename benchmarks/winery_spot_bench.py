"""Winery-membership spot-check (round 355): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月5日第一次在酒庄买酒，赤霞珠一瓶260元。",
        "kind": "episodic",
        "cues": ["2026-01-05", "赤霞珠"],
    },
    {
        "content": "2026年1月5日办理酒庄会员，年费500元。",
        "kind": "episodic",
        "cues": ["2026-01-05", "会员"],
    },
    {
        "content": "酒庄营业时间：早10点到晚8点。",
        "kind": "semantic",
        "cues": ["营业时间", "10点"],
    },
    {
        "content": "酒庄电话 0371-8888-6666。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "酒款种类：赤霞珠、梅洛、霞多丽、起泡酒、冰酒。",
        "kind": "semantic",
        "cues": ["酒款", "种类"],
    },
    {
        "content": "储存条件：恒温15度，避光保存。",
        "kind": "semantic",
        "cues": ["储存", "15度"],
    },
    {
        "content": "2026年2月2日预约2月14日品鉴会。",
        "kind": "episodic",
        "cues": ["2026-02-02", "品鉴会"],
    },
    {
        "content": "2026年2月14日品鉴会完成。",
        "kind": "episodic",
        "cues": ["2026-02-14", "品鉴会"],
    },
    {
        "content": "会员权益：会员购酒9折，生日赠酒一瓶。",
        "kind": "semantic",
        "cues": ["会员", "权益"],
    },
    {
        "content": "2026年3月8日购买梅洛两瓶，共420元。",
        "kind": "episodic",
        "cues": ["2026-03-08", "梅洛"],
    },
    {
        "content": "2026年3月15日收到梅洛配送。",
        "kind": "episodic",
        "cues": ["2026-03-15", "配送"],
    },
    {
        "content": "配送说明：满300元免费配送。",
        "kind": "semantic",
        "cues": ["配送", "说明"],
    },
    {
        "content": "2026年4月6日收到通知：4月20日春季酒会。",
        "kind": "episodic",
        "cues": ["2026-04-06", "酒会"],
    },
    {
        "content": "2026年4月20日春季酒会完成。",
        "kind": "episodic",
        "cues": ["2026-04-20", "酒会"],
    },
    {
        "content": "2026年5月10日预约5月24日品鉴冰酒。",
        "kind": "episodic",
        "cues": ["2026-05-10", "冰酒"],
    },
    {
        "content": "2026年5月24日冰酒品鉴完成。",
        "kind": "episodic",
        "cues": ["2026-05-24", "冰酒"],
    },
    {
        "content": "2026年6月8日收到通知：6月22日酿酒体验课。",
        "kind": "episodic",
        "cues": ["2026-06-08", "酿酒"],
    },
    {
        "content": "2026年6月22日酿酒体验课完成。",
        "kind": "episodic",
        "cues": ["2026-06-22", "酿酒"],
    },
    {
        "content": "2026年8月3日预约8月17日取酒。",
        "kind": "episodic",
        "cues": ["2026-08-03", "取酒"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日会员年费续费。",
        "kind": "episodic",
        "cues": ["2026-08-10", "年费"],
    },
]


QUESTIONS = [
    {
        "dim": "首次购买",
        "q": "第一次在酒庄买酒是什么时候？",
        "answer": "1月5日",
        "terms": ["5"],
    },
    {
        "dim": "红酒价格",
        "q": "赤霞珠一瓶多少钱？",
        "answer": "260元",
        "terms": ["260"],
    },
    {
        "dim": "下次取酒",
        "q": "下次取酒是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "酒庄几点开门？",
        "answer": "早10点",
        "terms": ["10"],
    },
    {
        "dim": "电话",
        "q": "酒庄电话多少？",
        "answer": "0371-8888-6666",
        "terms": ["6666"],
    },
    {
        "dim": "酒款种类",
        "q": "酒庄有哪些酒款？",
        "answer": "赤霞珠、梅洛、霞多丽、起泡酒、冰酒",
        "terms": ["起泡酒"],
    },
    {
        "dim": "储存条件",
        "q": "红酒怎么储存？",
        "answer": "恒温15度，避光",
        "terms": ["15度"],
    },
    {
        "dim": "会员权益",
        "q": "会员购酒打几折？",
        "answer": "9折",
        "terms": ["9"],
    },
    {
        "dim": "免费配送",
        "q": "满多少钱免费配送？",
        "answer": "300元",
        "terms": ["300"],
    },
    {
        "dim": "年费续费",
        "q": "会员年费什么时候续费？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="红酒酒庄会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="winery_mem0db",
        out_name="winery_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
