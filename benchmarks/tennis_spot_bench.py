"""Tennis-court spot-check (round 360): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月7日第一次预约网球场，场地费每小时100元。",
        "kind": "episodic",
        "cues": ["2026-01-07", "预约"],
    },
    {
        "content": "2026年1月10日第一次打球。",
        "kind": "episodic",
        "cues": ["2026-01-10", "打球"],
    },
    {
        "content": "网球场营业时间：早7点到晚10点。",
        "kind": "semantic",
        "cues": ["营业时间", "7点"],
    },
    {
        "content": "网球场电话 0351-6666-9999。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "设施：室内场2片、室外场4片、更衣室、淋浴。",
        "kind": "semantic",
        "cues": ["设施", "室内场"],
    },
    {
        "content": "2026年2月3日预约2月15日教练课。",
        "kind": "episodic",
        "cues": ["2026-02-03", "教练课"],
    },
    {
        "content": "2026年2月15日教练课完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "教练课"],
    },
    {
        "content": "2026年3月8日购买网球拍，价格680元。",
        "kind": "episodic",
        "cues": ["2026-03-08", "球拍"],
    },
    {
        "content": "会员优惠：会员订场8折。",
        "kind": "semantic",
        "cues": ["会员", "优惠"],
    },
    {
        "content": "2026年4月6日收到通知：4月20日春季网球赛。",
        "kind": "episodic",
        "cues": ["2026-04-06", "比赛"],
    },
    {
        "content": "2026年4月20日春季网球赛完成。",
        "kind": "episodic",
        "cues": ["2026-04-20", "比赛"],
    },
    {
        "content": "2026年5月10日预约5月24日双打场地。",
        "kind": "episodic",
        "cues": ["2026-05-10", "双打"],
    },
    {
        "content": "2026年5月24日双打完成。",
        "kind": "episodic",
        "cues": ["2026-05-24", "双打"],
    },
    {
        "content": "2026年6月8日收到通知：6月22日暑期训练营。",
        "kind": "episodic",
        "cues": ["2026-06-08", "训练营"],
    },
    {
        "content": "2026年6月22日训练营报名完成。",
        "kind": "episodic",
        "cues": ["2026-06-22", "训练营"],
    },
    {
        "content": "2026年7月10日预约7月24日早场。",
        "kind": "episodic",
        "cues": ["2026-07-10", "早场"],
    },
    {
        "content": "2026年7月24日早场完成。",
        "kind": "episodic",
        "cues": ["2026-07-24", "早场"],
    },
    {
        "content": "2026年8月4日预约8月17日下次场地。",
        "kind": "episodic",
        "cues": ["2026-08-04", "场地"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日会员年卡续费。",
        "kind": "episodic",
        "cues": ["2026-08-10", "年卡"],
    },
    {
        "content": "2026年8月12日收到通知：8月28日秋季公开赛。",
        "kind": "episodic",
        "cues": ["2026-08-12", "公开赛"],
    },
]


QUESTIONS = [
    {
        "dim": "首次预约",
        "q": "第一次预约网球场是什么时候？",
        "answer": "1月7日",
        "terms": ["7"],
    },
    {
        "dim": "场地费",
        "q": "场地费每小时多少钱？",
        "answer": "100元",
        "terms": ["100"],
    },
    {
        "dim": "下次场地",
        "q": "下次场地是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "网球场几点开门？",
        "answer": "早7点",
        "terms": ["7"],
    },
    {
        "dim": "电话",
        "q": "网球场电话多少？",
        "answer": "0351-6666-9999",
        "terms": ["9999"],
    },
    {
        "dim": "设施",
        "q": "球场有哪些设施？",
        "answer": "室内场2片、室外场4片、更衣室、淋浴",
        "terms": ["更衣室"],
    },
    {
        "dim": "球拍价格",
        "q": "网球拍多少钱？",
        "answer": "680元",
        "terms": ["680"],
    },
    {
        "dim": "会员优惠",
        "q": "会员订场打几折？",
        "answer": "8折",
        "terms": ["8"],
    },
    {
        "dim": "训练营",
        "q": "暑期训练营什么时候报名的？",
        "answer": "6月22日",
        "terms": ["22"],
    },
    {
        "dim": "年卡续费",
        "q": "会员年卡什么时候续费？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="网球场会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="tennis_mem0db",
        out_name="tennis_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
