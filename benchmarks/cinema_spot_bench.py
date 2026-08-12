"""Cinema & events spot-check (round 285): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日办会员卡：充值 200 送 40。",
        "kind": "episodic",
        "cues": ["2026-01-10", "会员卡"],
    },
    {
        "content": "2026年1月20日看《流浪地球3》：2D，35 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "流浪地球"],
    },
    {
        "content": "2026年2月14日情人节看《爱情神话2》：情侣座。",
        "kind": "episodic",
        "cues": ["2026-02-14", "爱情神话"],
    },
    {
        "content": "2026年3月1日会员积分 1200 分。",
        "kind": "episodic",
        "cues": ["2026-03-01", "积分"],
    },
    {
        "content": "2026年3月15日看《沙丘3》：IMAX，票价 45 元。",
        "kind": "episodic",
        "cues": ["2026-03-15", "沙丘"],
    },
    {
        "content": "2026年4月1日买演出票：话剧《茶馆》，4 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-04-01", "茶馆"],
    },
    {
        "content": "2026年4月20日看话剧《茶馆》。",
        "kind": "episodic",
        "cues": ["2026-04-20", "茶馆"],
    },
    {
        "content": "2026年5月1日预约 5 月 10 日看《灌篮高手》重映。",
        "kind": "episodic",
        "cues": ["2026-05-01", "灌篮高手"],
    },
    {
        "content": "2026年5月10日看《灌篮高手》。",
        "kind": "episodic",
        "cues": ["2026-05-10", "灌篮高手"],
    },
    {
        "content": "2026年6月1日买音乐会票：6 月 20 日，票价 280。",
        "kind": "episodic",
        "cues": ["2026-06-01", "音乐会"],
    },
    {
        "content": "2026年6月20日听音乐会。",
        "kind": "episodic",
        "cues": ["2026-06-20", "音乐会"],
    },
    {
        "content": "2026年7月1日影院会员日：每周三半价。",
        "kind": "semantic",
        "cues": ["会员日", "半价"],
    },
    {
        "content": "2026年7月10日看《默杀》：恐怖片，朋友不敢看。",
        "kind": "episodic",
        "cues": ["2026-07-10", "默杀"],
    },
    {
        "content": "2026年8月1日预约 8 月 15 日看《封神2》。",
        "kind": "episodic",
        "cues": ["2026-08-01", "封神"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 10 日会员积分过期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "积分"],
    },
    {
        "content": "影院地址：万达广场 5 楼。",
        "kind": "semantic",
        "cues": ["地址", "万达"],
    },
    {
        "content": "爆米花套餐：45 元。",
        "kind": "semantic",
        "cues": ["爆米花"],
    },
    {
        "content": "停车：凭电影票免 3 小时。",
        "kind": "semantic",
        "cues": ["停车"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日《异形》点映。",
        "kind": "episodic",
        "cues": ["2026-08-08", "异形"],
    },
    {
        "content": "会员电话 400-111-2222。",
        "kind": "semantic",
        "cues": ["会员", "电话"],
    },
    {
        "content": "2026年8月9日预约 8 月 18 日看《碟中谍9》。",
        "kind": "episodic",
        "cues": ["2026-08-09", "碟中谍"],
    },
]


QUESTIONS = [
    {
        "dim": "观影记录",
        "q": "上次看电影是什么时候？看的什么？",
        "answer": "7月10日，默杀",
        "terms": ["默杀"],
    },
    {
        "dim": "未来安排",
        "q": "下次看电影是什么时候？看哪部？",
        "answer": "8月15日封神2",
        "terms": ["封神"],
    },
    {
        "dim": "IMAX票价",
        "q": "IMAX 票价多少？",
        "answer": "45元",
        "terms": ["45"],
    },
    {
        "dim": "会员优惠",
        "q": "会员日什么时候？优惠是什么？",
        "answer": "每周三半价",
        "terms": ["半价"],
    },
    {
        "dim": "积分提醒",
        "q": "会员积分什么时候过期？",
        "answer": "8月10日",
        "terms": ["10"],
    },
    {
        "dim": "话剧记录",
        "q": "话剧《茶馆》什么时候看的？",
        "answer": "4月20日",
        "terms": ["20"],
    },
    {
        "dim": "音乐会票价",
        "q": "音乐会票价多少？",
        "answer": "280元",
        "terms": ["280"],
    },
    {
        "dim": "影院地址",
        "q": "影院在哪？",
        "answer": "万达广场5楼",
        "terms": ["万达"],
    },
    {
        "dim": "停车规则",
        "q": "停车怎么免？",
        "answer": "凭电影票免3小时",
        "terms": ["3"],
    },
    {
        "dim": "点映通知",
        "q": "《异形》点映什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="影院演出",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="cinema_mem0db",
        out_name="cinema_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
