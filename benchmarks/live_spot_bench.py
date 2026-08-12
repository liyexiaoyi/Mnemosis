"""Livestream-selling spot-check (round 271): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日注册直播账号，粉丝 0。",
        "kind": "episodic",
        "cues": ["2026-01-10", "账号"],
    },
    {
        "content": "2026年1月20日第一次直播：卖了 23 单，销售额 1800 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "直播"],
    },
    {
        "content": "2026年2月5日选品：小风扇 39 元，毛巾 15 元。",
        "kind": "semantic",
        "cues": ["选品", "小风扇"],
    },
    {
        "content": "2026年2月10日第二次直播：卖了 51 单，销售额 4200 元。",
        "kind": "episodic",
        "cues": ["2026-02-10", "直播"],
    },
    {
        "content": "2026年2月15日开通小店保证金 2000 元。",
        "kind": "episodic",
        "cues": ["2026-02-15", "保证金"],
    },
    {
        "content": "2026年3月1日直播时间改为每周二、五晚 8 点。",
        "kind": "semantic",
        "cues": ["直播时间"],
    },
    {
        "content": "2026年3月10日第三次直播：卖了 88 单。",
        "kind": "episodic",
        "cues": ["2026-03-10", "直播"],
    },
    {
        "content": "2026年3月15日收到平台通知：3 月 25 日大促活动报名截止。",
        "kind": "episodic",
        "cues": ["2026-03-15", "大促"],
    },
    {
        "content": "2026年3月25日报名大促成功。",
        "kind": "episodic",
        "cues": ["2026-03-25", "大促"],
    },
    {
        "content": "2026年4月1日大促直播：卖了 300 单，销售额 2.4 万。",
        "kind": "episodic",
        "cues": ["2026-04-01", "大促"],
    },
    {
        "content": "2026年4月5日退货率 12%，客服说偏高。",
        "kind": "episodic",
        "cues": ["2026-04-05", "退货率"],
    },
    {
        "content": "2026年4月20日换主播小美：周日晚播。",
        "kind": "semantic",
        "cues": ["主播", "小美"],
    },
    {
        "content": "2026年5月1日小美首播：卖了 150 单。",
        "kind": "episodic",
        "cues": ["2026-05-01", "小美"],
    },
    {
        "content": "2026年5月10日收到样品：手持挂烫机 129 元。",
        "kind": "episodic",
        "cues": ["2026-05-10", "挂烫机"],
    },
    {
        "content": "2026年5月15日挂烫机专场：卖了 96 台。",
        "kind": "episodic",
        "cues": ["2026-05-15", "挂烫机"],
    },
    {
        "content": "2026年6月1日粉丝破 1 万。",
        "kind": "episodic",
        "cues": ["2026-06-01", "粉丝"],
    },
    {
        "content": "2026年6月10日预约 6 月 20 日户外直播。",
        "kind": "episodic",
        "cues": ["2026-06-10", "户外"],
    },
    {
        "content": "2026年6月20日户外直播：卖了 45 单。",
        "kind": "episodic",
        "cues": ["2026-06-20", "户外"],
    },
    {
        "content": "2026年7月1日供货商涨价：小风扇涨到 45 元。",
        "kind": "episodic",
        "cues": ["2026-07-01", "涨价"],
    },
    {
        "content": "2026年7月10日直播违规提醒：7 月 15 日前整改。",
        "kind": "episodic",
        "cues": ["2026-07-10", "违规"],
    },
    {
        "content": "2026年7月15日整改完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "整改"],
    },
    {
        "content": "2026年7月20日预约 8 月 20 日新品发布会直播。",
        "kind": "episodic",
        "cues": ["2026-07-20", "发布会"],
    },
    {
        "content": "2026年7月25日快递合作：全国包邮首重 5 元。",
        "kind": "semantic",
        "cues": ["快递", "包邮"],
    },
    {
        "content": "2026年8月1日粉丝团改价：铁粉价 9 折。",
        "kind": "semantic",
        "cues": ["铁粉价"],
    },
    {
        "content": "2026年8月6日收到平台账单：7 月佣金 8600 元。",
        "kind": "episodic",
        "cues": ["2026-08-06", "佣金"],
    },
    {
        "content": "直播话术：开场 3 分钟抽奖。",
        "kind": "semantic",
        "cues": ["话术"],
    },
]


QUESTIONS = [
    {
        "dim": "直播业绩",
        "q": "上次直播是什么时候？卖了多少单？",
        "answer": "6月20日，45单",
        "terms": ["45"],
    },
    {
        "dim": "未来安排",
        "q": "下次直播是什么时候？",
        "answer": "8月20日新品发布会",
        "terms": ["20"],
    },
    {
        "dim": "选品价格",
        "q": "小风扇现在多少钱？",
        "answer": "45元",
        "terms": ["45"],
    },
    {
        "dim": "大促数据",
        "q": "大促直播卖了多少单？销售额多少？",
        "answer": "300单，2.4万",
        "terms": ["300"],
    },
    {
        "dim": "平台规则",
        "q": "退货率是多少？",
        "answer": "12%",
        "terms": ["12"],
    },
    {
        "dim": "主播安排",
        "q": "现在主播是谁？什么时候播？",
        "answer": "小美，周日晚播",
        "terms": ["小美"],
    },
    {
        "dim": "粉丝增长",
        "q": "粉丝什么时候破万的？",
        "answer": "6月1日",
        "terms": ["1"],
    },
    {
        "dim": "违规整改",
        "q": "上次违规整改是什么时候完成的？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "物流合作",
        "q": "快递合作怎么算？",
        "answer": "全国包邮首重5元",
        "terms": ["5"],
    },
    {
        "dim": "佣金账单",
        "q": "7月佣金多少？",
        "answer": "8600元",
        "terms": ["8600"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="直播带货",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="live_mem0db",
        out_name="live_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
