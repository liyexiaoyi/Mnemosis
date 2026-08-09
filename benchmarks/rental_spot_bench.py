"""House-rental spot-check (round 268): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年2月1日找中介看房，预算 4500 元/月。",
        "kind": "episodic",
        "cues": ["2026-02-01", "中介"],
    },
    {
        "content": "2026年2月5日看了 A 小区两居：4200 元/月。",
        "kind": "episodic",
        "cues": ["2026-02-05", "A小区"],
    },
    {
        "content": "2026年2月8日看了 B 小区一居：3800 元/月。",
        "kind": "episodic",
        "cues": ["2026-02-08", "B小区"],
    },
    {
        "content": "2026年2月12日定下 A 小区两居：押一付三。",
        "kind": "episodic",
        "cues": ["2026-02-12", "A小区"],
    },
    {
        "content": "2026年2月15日签合同：租期 1 年，2026 年 3 月 1 日起租，合同号 ZL-2026-0215。",
        "kind": "semantic",
        "cues": ["合同", "ZL-2026-0215"],
    },
    {
        "content": "2026年2月20日付押金 4200 元和首月房租 4200 元。",
        "kind": "episodic",
        "cues": ["2026-02-20", "押金"],
    },
    {
        "content": "2026年2月25日收房检查：热水器有点问题，房东 3 月 2 日来修。",
        "kind": "episodic",
        "cues": ["2026-02-25", "收房"],
    },
    {
        "content": "2026年3月1日入住 A 小区 3 栋 502。",
        "kind": "episodic",
        "cues": ["2026-03-01", "入住"],
    },
    {
        "content": "2026年3月2日热水器修好了。",
        "kind": "episodic",
        "cues": ["2026-03-02", "热水器"],
    },
    {
        "content": "2026年3月10日电费户号绑定：每月 15 号出账单。",
        "kind": "semantic",
        "cues": ["电费", "15号"],
    },
    {
        "content": "2026年3月20日第一次交水电费 186 元。",
        "kind": "episodic",
        "cues": ["2026-03-20", "水电费"],
    },
    {
        "content": "2026年4月10日物业通知：4 月 20 日电梯检修。",
        "kind": "episodic",
        "cues": ["2026-04-10", "电梯"],
    },
    {
        "content": "2026年4月20日电梯检修完成。",
        "kind": "episodic",
        "cues": ["2026-04-20", "电梯"],
    },
    {
        "content": "2026年5月1日房东说 5 月 10 日来查房。",
        "kind": "episodic",
        "cues": ["2026-05-01", "查房"],
    },
    {
        "content": "2026年5月10日查房通过。",
        "kind": "episodic",
        "cues": ["2026-05-10", "查房"],
    },
    {
        "content": "2026年5月15日申请换纱窗，物业 5 月 20 日来换。",
        "kind": "episodic",
        "cues": ["2026-05-15", "纱窗"],
    },
    {
        "content": "2026年5月20日纱窗换好。",
        "kind": "episodic",
        "cues": ["2026-05-20", "纱窗"],
    },
    {
        "content": "2026年6月1日交第二季度房租：3 个月共 12600 元。",
        "kind": "episodic",
        "cues": ["2026-06-01", "房租"],
    },
    {
        "content": "2026年6月10日邻居投诉空调滴水，物业 6 月 15 日处理。",
        "kind": "episodic",
        "cues": ["2026-06-10", "空调"],
    },
    {
        "content": "2026年6月15日空调滴水修好。",
        "kind": "episodic",
        "cues": ["2026-06-15", "空调"],
    },
    {
        "content": "2026年7月1日燃气充值 200 元。",
        "kind": "episodic",
        "cues": ["2026-07-01", "燃气"],
    },
    {
        "content": "2026年7月10日房东提醒 8 月 1 日前续租决定。",
        "kind": "episodic",
        "cues": ["2026-07-10", "续租"],
    },
    {
        "content": "2026年7月20日决定续租，8 月 1 日签续租合同。",
        "kind": "episodic",
        "cues": ["2026-07-20", "续租"],
    },
    {
        "content": "2026年8月2日续租成功：租到 2027 年 2 月 28 日，月租不变。",
        "kind": "episodic",
        "cues": ["2026-08-02", "续租"],
    },
    {
        "content": "2026年8月5日预约 8 月 15 日家政深度保洁。",
        "kind": "episodic",
        "cues": ["2026-08-05", "保洁"],
    },
    {
        "content": "2026年8月8日收到快递柜取件码 8842，晚上去取。",
        "kind": "episodic",
        "cues": ["2026-08-08", "取件码"],
    },
    {
        "content": "门禁密码 3311，快递放 1 号柜。",
        "kind": "semantic",
        "cues": ["门禁", "3311"],
    },
]


QUESTIONS = [
    {
        "dim": "房源对比",
        "q": "A 小区两居月租多少？",
        "answer": "4200元",
        "terms": ["4200"],
    },
    {
        "dim": "合同信息",
        "q": "合同号是多少？租期多久？",
        "answer": "ZL-2026-0215，1年",
        "terms": ["ZL-2026-0215"],
    },
    {
        "dim": "付款记录",
        "q": "押金多少？首月房租多少？",
        "answer": "押金4200，首月4200",
        "terms": ["4200"],
    },
    {
        "dim": "维修记录",
        "q": "上次维修是什么时候？修的什么？",
        "answer": "6月15日，空调滴水",
        "terms": ["空调"],
    },
    {
        "dim": "未来安排",
        "q": "下次家政保洁是什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "续租状态",
        "q": "续租了吗？租到什么时候？",
        "answer": "续租成功，租到2027年2月28日",
        "terms": ["2027"],
    },
    {
        "dim": "水电账单",
        "q": "水电费什么时候出账单？上次交了多少？",
        "answer": "每月15号出账单，上次交186元",
        "terms": ["15", "186"],
    },
    {
        "dim": "门禁信息",
        "q": "门禁密码多少？快递放哪？",
        "answer": "3311，1号柜",
        "terms": ["3311"],
    },
    {
        "dim": "查房记录",
        "q": "上次查房是什么时候？结果如何？",
        "answer": "5月10日，通过",
        "terms": ["通过"],
    },
    {
        "dim": "设施检修",
        "q": "电梯检修是什么时候完成的？",
        "answer": "4月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="房屋租赁",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="rental_mem0db",
        out_name="rental_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
