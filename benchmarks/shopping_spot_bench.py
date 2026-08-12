"""Online-shopping after-sales spot-check (round 275): Mnemosis vs mem0."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买手机壳 29 元，订单号 DD-2026-0110。",
        "kind": "episodic",
        "cues": ["2026-01-10", "手机壳", "DD-2026-0110"],
    },
    {
        "content": "2026年1月15日手机壳到货，质量一般。",
        "kind": "episodic",
        "cues": ["2026-01-15", "手机壳"],
    },
    {
        "content": "2026年2月1日买羽绒服 599 元，2 月 5 日到货。",
        "kind": "episodic",
        "cues": ["2026-02-01", "羽绒服"],
    },
    {
        "content": "2026年2月8日羽绒服尺码偏大，申请退货。",
        "kind": "episodic",
        "cues": ["2026-02-08", "退货"],
    },
    {
        "content": "2026年2月12日退货成功，退款 599 元。",
        "kind": "episodic",
        "cues": ["2026-02-12", "退货"],
    },
    {
        "content": "2026年3月1日买跑步鞋 399 元。",
        "kind": "episodic",
        "cues": ["2026-03-01", "跑步鞋"],
    },
    {
        "content": "2026年3月10日跑步鞋磨脚，3 月 15 日换货。",
        "kind": "episodic",
        "cues": ["2026-03-10", "换货"],
    },
    {
        "content": "2026年3月18日换货收到新鞋。",
        "kind": "episodic",
        "cues": ["2026-03-18", "换货"],
    },
    {
        "content": "2026年4月1日买台灯 129 元，质保 1 年。",
        "kind": "episodic",
        "cues": ["2026-04-01", "台灯"],
    },
    {
        "content": "2026年4月10日台灯闪烁，联系客服。",
        "kind": "episodic",
        "cues": ["2026-04-10", "台灯"],
    },
    {
        "content": "2026年4月20日客服安排 4 月 25 日上门换新。",
        "kind": "episodic",
        "cues": ["2026-04-20", "换新"],
    },
    {
        "content": "2026年4月25日台灯换新完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "换新"],
    },
    {
        "content": "2026年5月1日会员日 88 折，买洗衣液。",
        "kind": "episodic",
        "cues": ["2026-05-01", "会员日"],
    },
    {
        "content": "2026年5月15日快递柜取件码 5566。",
        "kind": "episodic",
        "cues": ["2026-05-15", "取件码"],
    },
    {
        "content": "2026年6月1日买电饭煲 349 元，赠品锅铲。",
        "kind": "episodic",
        "cues": ["2026-06-01", "电饭煲"],
    },
    {
        "content": "2026年6月10日电饭煲蒸笼变形，申请售后。",
        "kind": "episodic",
        "cues": ["2026-06-10", "售后"],
    },
    {
        "content": "2026年6月18日售后同意补发蒸笼。",
        "kind": "episodic",
        "cues": ["2026-06-18", "蒸笼"],
    },
    {
        "content": "2026年6月25日收到补发蒸笼。",
        "kind": "episodic",
        "cues": ["2026-06-25", "蒸笼"],
    },
    {
        "content": "2026年7月1日买猫粮 268 元。",
        "kind": "episodic",
        "cues": ["2026-07-01", "猫粮"],
    },
    {
        "content": "2026年7月10日猫粮破损，申请退款。",
        "kind": "episodic",
        "cues": ["2026-07-10", "退款"],
    },
    {
        "content": "2026年7月15日退款 268 元到账。",
        "kind": "episodic",
        "cues": ["2026-07-15", "退款"],
    },
    {
        "content": "2026年7月20日会员积分 3200 分。",
        "kind": "episodic",
        "cues": ["2026-07-20", "积分"],
    },
    {
        "content": "2026年8月1日买耳机 199 元，预约 8 月 14 日到货。",
        "kind": "episodic",
        "cues": ["2026-08-01", "耳机"],
    },
    {
        "content": "2026年8月5日客服说 8 月 20 日大促开始。",
        "kind": "episodic",
        "cues": ["2026-08-05", "大促"],
    },
    {
        "content": "退货政策：7 天无理由。",
        "kind": "semantic",
        "cues": ["退货政策"],
    },
    {
        "content": "客服电话 400-800-8888。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "订单记录",
        "q": "手机壳订单号多少？",
        "answer": "DD-2026-0110",
        "terms": ["DD"],
    },
    {
        "dim": "退货记录",
        "q": "上次退款是什么时候？退了多少钱？",
        "answer": "7月15日，268元",
        "terms": ["268"],
    },
    {
        "dim": "换货记录",
        "q": "上次换货是什么时候？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "未来安排",
        "q": "耳机什么时候到货？",
        "answer": "8月14日",
        "terms": ["14"],
    },
    {
        "dim": "台灯售后",
        "q": "台灯什么问题？怎么解决的？",
        "answer": "闪烁，4月25日上门换新",
        "terms": ["换新"],
    },
    {
        "dim": "电饭煲",
        "q": "电饭煲赠品是什么？",
        "answer": "锅铲",
        "terms": ["锅铲"],
    },
    {
        "dim": "会员权益",
        "q": "会员日折扣多少？积分多少？",
        "answer": "88折，3200分",
        "terms": ["88", "3200"],
    },
    {
        "dim": "退货政策",
        "q": "退货政策是什么？",
        "answer": "7天无理由",
        "terms": ["7"],
    },
    {
        "dim": "客服电话",
        "q": "客服电话多少？",
        "answer": "400-800-8888",
        "terms": ["8888"],
    },
    {
        "dim": "大促安排",
        "q": "下次大促什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="网购售后",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="shopping_mem0db",
        out_name="shopping_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
