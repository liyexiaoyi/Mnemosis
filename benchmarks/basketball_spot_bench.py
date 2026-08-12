"""Basketball-gym spot-check (round 363): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月5日第一次预约篮球馆，办月卡300元。",
        "kind": "episodic",
        "cues": ["2026-01-05", "月卡"],
    },
    {
        "content": "2026年1月9日第一次打球。",
        "kind": "episodic",
        "cues": ["2026-01-09", "打球"],
    },
    {
        "content": "篮球馆营业时间：早8点到晚10点。",
        "kind": "semantic",
        "cues": ["营业时间", "8点"],
    },
    {
        "content": "篮球馆电话 0471-6666-8888。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "设施：全场2片、半场4片、更衣室、自动售货机。",
        "kind": "semantic",
        "cues": ["设施", "全场"],
    },
    {
        "content": "2026年2月2日预约2月14日全场。",
        "kind": "episodic",
        "cues": ["2026-02-02", "全场"],
    },
    {
        "content": "2026年2月14日全场打球完成。",
        "kind": "episodic",
        "cues": ["2026-02-14", "全场"],
    },
    {
        "content": "2026年3月8日收到通知：3月22日篮球赛。",
        "kind": "episodic",
        "cues": ["2026-03-08", "篮球赛"],
    },
    {
        "content": "2026年3月22日篮球赛完成。",
        "kind": "episodic",
        "cues": ["2026-03-22", "篮球赛"],
    },
    {
        "content": "会员优惠：会员订场8折。",
        "kind": "semantic",
        "cues": ["会员", "优惠"],
    },
    {
        "content": "2026年4月10日预约4月24日半场。",
        "kind": "episodic",
        "cues": ["2026-04-10", "半场"],
    },
    {
        "content": "2026年4月24日半场打球完成。",
        "kind": "episodic",
        "cues": ["2026-04-24", "半场"],
    },
    {
        "content": "2026年5月8日收到通知：5月22日夏季联赛。",
        "kind": "episodic",
        "cues": ["2026-05-08", "联赛"],
    },
    {
        "content": "2026年5月22日联赛报名完成。",
        "kind": "episodic",
        "cues": ["2026-05-22", "联赛"],
    },
    {
        "content": "2026年6月10日预约6月24日早场。",
        "kind": "episodic",
        "cues": ["2026-06-10", "早场"],
    },
    {
        "content": "2026年6月24日早场完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "早场"],
    },
    {
        "content": "2026年7月8日收到通知：7月22日青少年训练营。",
        "kind": "episodic",
        "cues": ["2026-07-08", "训练营"],
    },
    {
        "content": "2026年8月4日预约8月17日下次打球。",
        "kind": "episodic",
        "cues": ["2026-08-04", "打球"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日月卡续费。",
        "kind": "episodic",
        "cues": ["2026-08-10", "月卡"],
    },
    {
        "content": "2026年8月12日收到通知：8月28日秋季联赛。",
        "kind": "episodic",
        "cues": ["2026-08-12", "联赛"],
    },
]


QUESTIONS = [
    {
        "dim": "首次办卡",
        "q": "篮球馆月卡第一次什么时候办的？",
        "answer": "1月5日",
        "terms": ["5"],
    },
    {
        "dim": "月卡价格",
        "q": "篮球馆月卡多少钱？",
        "answer": "300元",
        "terms": ["300"],
    },
    {
        "dim": "下次打球",
        "q": "下次打球是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "篮球馆几点开门？",
        "answer": "早8点",
        "terms": ["8"],
    },
    {
        "dim": "电话",
        "q": "篮球馆电话多少？",
        "answer": "0471-6666-8888",
        "terms": ["8888"],
    },
    {
        "dim": "设施",
        "q": "篮球馆有哪些设施？",
        "answer": "全场2片、半场4片、更衣室、自动售货机",
        "terms": ["自动售货机"],
    },
    {
        "dim": "会员优惠",
        "q": "会员订场打几折？",
        "answer": "8折",
        "terms": ["8"],
    },
    {
        "dim": "篮球赛",
        "q": "篮球赛什么时候？",
        "answer": "3月22日",
        "terms": ["22"],
    },
    {
        "dim": "训练营",
        "q": "青少年训练营什么时候？",
        "answer": "7月22日",
        "terms": ["22"],
    },
    {
        "dim": "月卡续费",
        "q": "月卡什么时候续费？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="篮球馆会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="basketball_mem0db",
        out_name="basketball_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
