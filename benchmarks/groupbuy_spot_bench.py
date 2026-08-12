"""Community group-buying spot-check (round 279): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日加入小区团购群。",
        "kind": "episodic",
        "cues": ["2026-01-10", "团购群"],
    },
    {
        "content": "2026年1月15日第一次团购：水果 58 元。",
        "kind": "episodic",
        "cues": ["2026-01-15", "团购"],
    },
    {
        "content": "2026年2月1日团购规则：满 50 免配送费。",
        "kind": "semantic",
        "cues": ["团购规则", "50"],
    },
    {
        "content": "2026年2月10日团购鸡蛋：30 个 25 元。",
        "kind": "episodic",
        "cues": ["2026-02-10", "鸡蛋"],
    },
    {
        "content": "2026年3月1日团长换人：新团长小王。",
        "kind": "semantic",
        "cues": ["团长", "小王"],
    },
    {
        "content": "2026年3月15日团购蔬菜包：39.9 元。",
        "kind": "episodic",
        "cues": ["2026-03-15", "蔬菜"],
    },
    {
        "content": "2026年4月1日团购群改规则：每周三截单。",
        "kind": "semantic",
        "cues": ["截单", "周三"],
    },
    {
        "content": "2026年4月10日团购牛奶：2 箱 88 元。",
        "kind": "episodic",
        "cues": ["2026-04-10", "牛奶"],
    },
    {
        "content": "2026年5月1日提货点改到 3 栋楼下。",
        "kind": "semantic",
        "cues": ["提货", "3栋"],
    },
    {
        "content": "2026年5月15日团购海鲜：虾 68 元。",
        "kind": "episodic",
        "cues": ["2026-05-15", "海鲜"],
    },
    {
        "content": "2026年6月1日收到通知：6 月 10 日冷链配送。",
        "kind": "episodic",
        "cues": ["2026-06-01", "冷链"],
    },
    {
        "content": "2026年6月10日冷链海鲜到货。",
        "kind": "episodic",
        "cues": ["2026-06-10", "冷链"],
    },
    {
        "content": "2026年7月1日团购大米：50 斤 128 元。",
        "kind": "episodic",
        "cues": ["2026-07-01", "大米"],
    },
    {
        "content": "2026年7月10日米有虫，申请售后。",
        "kind": "episodic",
        "cues": ["2026-07-10", "售后"],
    },
    {
        "content": "2026年7月15日售后退款 128 元。",
        "kind": "episodic",
        "cues": ["2026-07-15", "售后"],
    },
    {
        "content": "2026年7月20日团购群公告：8 月 1 日起改每日截单。",
        "kind": "episodic",
        "cues": ["2026-07-20", "截单"],
    },
    {
        "content": "2026年8月1日新规则生效。",
        "kind": "episodic",
        "cues": ["2026-08-01", "截单"],
    },
    {
        "content": "2026年8月5日预约 8 月 12 日团购龙虾。",
        "kind": "episodic",
        "cues": ["2026-08-05", "龙虾"],
    },
    {
        "content": "2026年8月8日团长说 8 月 20 日小区团购节。",
        "kind": "episodic",
        "cues": ["2026-08-08", "团购节"],
    },
    {
        "content": "提货时间：每周四 17:00-19:00。",
        "kind": "semantic",
        "cues": ["提货时间"],
    },
    {
        "content": "团购客服 400-666-8888。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "退款规则：质量问题 48 小时内处理。",
        "kind": "semantic",
        "cues": ["退款", "48"],
    },
    {
        "content": "2026年8月9日预约 8 月 15 日团购牛排。",
        "kind": "episodic",
        "cues": ["2026-08-09", "牛排"],
    },
]


QUESTIONS = [
    {
        "dim": "团购规则",
        "q": "团购满多少免配送费？",
        "answer": "50元",
        "terms": ["50"],
    },
    {
        "dim": "团长信息",
        "q": "团长是谁？",
        "answer": "小王",
        "terms": ["小王"],
    },
    {
        "dim": "截单规则",
        "q": "现在什么时候截单？",
        "answer": "每日截单",
        "terms": ["每日"],
    },
    {
        "dim": "售后记录",
        "q": "上次售后是什么时候？退了多少钱？",
        "answer": "7月15日，128元",
        "terms": ["128"],
    },
    {
        "dim": "未来安排",
        "q": "下次团购龙虾是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "提货信息",
        "q": "提货时间是什么时候？在哪提？",
        "answer": "周四17:00-19:00，3栋楼下",
        "terms": ["17"],
    },
    {
        "dim": "大米售后",
        "q": "大米多少钱？出了什么问题？",
        "answer": "128元，有虫",
        "terms": ["虫"],
    },
    {
        "dim": "团购节",
        "q": "小区团购节什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "客服电话",
        "q": "团购客服电话多少？",
        "answer": "400-666-8888",
        "terms": ["8888"],
    },
    {
        "dim": "退款规则",
        "q": "质量问题多久处理？",
        "answer": "48小时内",
        "terms": ["48"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="社区团购",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="groupbuy_mem0db",
        out_name="groupbuy_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
