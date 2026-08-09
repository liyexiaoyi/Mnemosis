"""Restaurant-business spot-check (round 270): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月8日盘下小店：转让费 8 万，月租 6000 元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "转让费"],
    },
    {
        "content": "2026年1月15日办营业执照：食品经营许可证 2 月 1 日下来。",
        "kind": "episodic",
        "cues": ["2026-01-15", "执照"],
    },
    {
        "content": "2026年2月1日拿到食品经营许可证，店名“阿凯小面”。",
        "kind": "episodic",
        "cues": ["2026-02-01", "许可证"],
    },
    {
        "content": "2026年2月10日试营业：招牌牛肉面 18 元。",
        "kind": "episodic",
        "cues": ["2026-02-10", "试营业"],
    },
    {
        "content": "2026年2月20日正式开业。",
        "kind": "episodic",
        "cues": ["2026-02-20", "开业"],
    },
    {
        "content": "2026年3月5日供应商报价：面粉 2.4 元/斤，牛肉 32 元/斤。",
        "kind": "semantic",
        "cues": ["供应商", "报价"],
    },
    {
        "content": "2026年3月10日第一次盘点：牛肉面日销 80 碗。",
        "kind": "episodic",
        "cues": ["2026-03-10", "盘点"],
    },
    {
        "content": "2026年4月1日交季度房租 18000 元。",
        "kind": "episodic",
        "cues": ["2026-04-01", "房租"],
    },
    {
        "content": "2026年4月15日收到卫生检查通知：4 月 25 日检查后厨。",
        "kind": "episodic",
        "cues": ["2026-04-15", "卫生"],
    },
    {
        "content": "2026年4月25日卫生检查通过。",
        "kind": "episodic",
        "cues": ["2026-04-25", "卫生"],
    },
    {
        "content": "2026年5月5日上了新品：豌杂面 22 元。",
        "kind": "episodic",
        "cues": ["2026-05-05", "新品"],
    },
    {
        "content": "2026年5月20日美团抽成改到 15%。",
        "kind": "semantic",
        "cues": ["美团", "抽成"],
    },
    {
        "content": "2026年6月1日第二次盘点：牛肉面日销 120 碗。",
        "kind": "episodic",
        "cues": ["2026-06-01", "盘点"],
    },
    {
        "content": "2026年6月10日店员小刘请假：6 月 12 日到 6 月 18 日。",
        "kind": "episodic",
        "cues": ["2026-06-10", "请假"],
    },
    {
        "content": "2026年6月15日高峰时段排队超过 20 分钟。",
        "kind": "episodic",
        "cues": ["2026-06-15", "排队"],
    },
    {
        "content": "2026年7月1日第三季度房租 18000 元已交。",
        "kind": "episodic",
        "cues": ["2026-07-01", "房租"],
    },
    {
        "content": "2026年7月10日隔壁奶茶店转让，老板问要不要接。",
        "kind": "episodic",
        "cues": ["2026-07-10", "转让"],
    },
    {
        "content": "2026年7月18日决定不接奶茶店：资金不够。",
        "kind": "episodic",
        "cues": ["2026-07-18", "转让"],
    },
    {
        "content": "2026年7月25日预约 8 月 20 日更换燃气软管。",
        "kind": "episodic",
        "cues": ["2026-07-25", "燃气"],
    },
    {
        "content": "2026年8月1日收银系统升级：8 月 3 日凌晨维护。",
        "kind": "episodic",
        "cues": ["2026-08-01", "收银"],
    },
    {
        "content": "2026年8月4日美团客服说 8 月 10 日有满减活动报名。",
        "kind": "episodic",
        "cues": ["2026-08-04", "满减"],
    },
    {
        "content": "2026年8月6日店里装了新空调：2.5 匹，6500 元。",
        "kind": "episodic",
        "cues": ["2026-08-06", "空调"],
    },
    {
        "content": "进货渠道：牛肉找老李，面粉找刘姐。",
        "kind": "semantic",
        "cues": ["进货"],
    },
    {
        "content": "营业时间：早 8 点到晚 10 点，周一休息。",
        "kind": "semantic",
        "cues": ["营业时间"],
    },
    {
        "content": "招牌面配方：牛骨汤熬 6 小时，辣油 3 勺。",
        "kind": "semantic",
        "cues": ["配方"],
    },
    {
        "content": "员工排班：小刘早班，小王晚班，周日轮换。",
        "kind": "semantic",
        "cues": ["排班"],
    },
]


QUESTIONS = [
    {
        "dim": "开店成本",
        "q": "转让费多少？月租多少？",
        "answer": "转让费8万，月租6000",
        "terms": ["6000"],
    },
    {
        "dim": "证件日期",
        "q": "食品经营许可证什么时候拿到的？",
        "answer": "2月1日",
        "terms": ["1"],
    },
    {
        "dim": "菜品价格",
        "q": "招牌牛肉面多少钱？豌杂面呢？",
        "answer": "牛肉面18元，豌杂面22元",
        "terms": ["18", "22"],
    },
    {
        "dim": "经营数据",
        "q": "最近一次盘点牛肉面日销多少碗？",
        "answer": "120碗",
        "terms": ["120"],
    },
    {
        "dim": "平台规则",
        "q": "美团抽成是多少？",
        "answer": "15%",
        "terms": ["15"],
    },
    {
        "dim": "卫生检查",
        "q": "上次卫生检查是什么时候？结果如何？",
        "answer": "4月25日，通过",
        "terms": ["通过"],
    },
    {
        "dim": "未来安排",
        "q": "下次更换燃气软管是什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "营业时间",
        "q": "营业时间是几点到几点？哪天休息？",
        "answer": "早8点到晚10点，周一休息",
        "terms": ["10", "周一"],
    },
    {
        "dim": "进货渠道",
        "q": "牛肉找谁进货？",
        "answer": "老李",
        "terms": ["老李"],
    },
    {
        "dim": "决策记录",
        "q": "隔壁奶茶店为什么没接？",
        "answer": "资金不够",
        "terms": ["资金"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="餐饮经营",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="food_mem0db",
        out_name="food_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
