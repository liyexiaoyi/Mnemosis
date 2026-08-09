"""Coffee-shop spot-check (round 294): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日第一次去楼下咖啡店。",
        "kind": "episodic",
        "cues": ["2026-01-10", "咖啡店"],
    },
    {
        "content": "2026年1月20日办会员卡：充 300 送 60。",
        "kind": "episodic",
        "cues": ["2026-01-20", "会员卡"],
    },
    {
        "content": "2026年2月1日常点拿铁：大杯 32 元。",
        "kind": "semantic",
        "cues": ["拿铁", "32"],
    },
    {
        "content": "2026年2月15日会员日：每周二第二杯半价。",
        "kind": "semantic",
        "cues": ["会员日", "半价"],
    },
    {
        "content": "2026年3月1日预约 3 月 10 日学拉花课。",
        "kind": "episodic",
        "cues": ["2026-03-01", "拉花"],
    },
    {
        "content": "2026年3月10日拉花课完成。",
        "kind": "episodic",
        "cues": ["2026-03-10", "拉花"],
    },
    {
        "content": "2026年4月1日咖啡店换菜单：新品燕麦拿铁 38 元。",
        "kind": "episodic",
        "cues": ["2026-04-01", "燕麦拿铁"],
    },
    {
        "content": "2026年4月15日积分兑换：500 分换一杯。",
        "kind": "semantic",
        "cues": ["积分", "500"],
    },
    {
        "content": "2026年5月1日买咖啡豆：耶加雪菲 120 元/250g。",
        "kind": "episodic",
        "cues": ["2026-05-01", "咖啡豆"],
    },
    {
        "content": "2026年5月20日自己手冲。",
        "kind": "episodic",
        "cues": ["2026-05-20", "手冲"],
    },
    {
        "content": "2026年6月1日咖啡机清洗：6 月 5 日。",
        "kind": "episodic",
        "cues": ["2026-06-01", "清洗"],
    },
    {
        "content": "2026年6月5日咖啡机清洗完成。",
        "kind": "episodic",
        "cues": ["2026-06-05", "清洗"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日咖啡品鉴会。",
        "kind": "episodic",
        "cues": ["2026-07-01", "品鉴会"],
    },
    {
        "content": "2026年7月10日品鉴会：喝了 5 款豆子。",
        "kind": "episodic",
        "cues": ["2026-07-10", "品鉴会"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日取蛋糕。",
        "kind": "episodic",
        "cues": ["2026-08-01", "蛋糕"],
    },
    {
        "content": "2026年8月5日收到通知：8 月 20 日会员答谢日。",
        "kind": "episodic",
        "cues": ["2026-08-05", "答谢日"],
    },
    {
        "content": "咖啡师小周。",
        "kind": "semantic",
        "cues": ["咖啡师", "小周"],
    },
    {
        "content": "咖啡店营业：7:00-21:00。",
        "kind": "semantic",
        "cues": ["营业时间"],
    },
    {
        "content": "2026年8月8日收到提醒：8 月 15 日会员卡到期。",
        "kind": "episodic",
        "cues": ["2026-08-08", "到期"],
    },
]


QUESTIONS = [
    {
        "dim": "会员卡",
        "q": "会员卡充多少送多少？",
        "answer": "充300送60",
        "terms": ["300", "60"],
    },
    {
        "dim": "常点咖啡",
        "q": "常点什么咖啡？多少钱？",
        "answer": "大杯拿铁32元",
        "terms": ["拿铁", "32"],
    },
    {
        "dim": "会员优惠",
        "q": "会员日什么时候？优惠？",
        "answer": "每周二第二杯半价",
        "terms": ["半价"],
    },
    {
        "dim": "未来安排",
        "q": "下次取蛋糕是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "拉花课",
        "q": "拉花课什么时候上的？",
        "answer": "3月10日",
        "terms": ["10"],
    },
    {
        "dim": "新品价格",
        "q": "新品燕麦拿铁多少钱？",
        "answer": "38元",
        "terms": ["38"],
    },
    {
        "dim": "积分兑换",
        "q": "积分多少换一杯？",
        "answer": "500分",
        "terms": ["500"],
    },
    {
        "dim": "咖啡豆",
        "q": "咖啡豆多少钱？",
        "answer": "120元/250g",
        "terms": ["120"],
    },
    {
        "dim": "咖啡师",
        "q": "咖啡师叫什么？",
        "answer": "小周",
        "terms": ["小周"],
    },
    {
        "dim": "答谢日",
        "q": "会员答谢日什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="咖啡店会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="coffee_mem0db",
        out_name="coffee_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
