"""Investing spot-check (round 273): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日开户：某券商，佣金万1.5。",
        "kind": "episodic",
        "cues": ["2026-01-10", "开户"],
    },
    {
        "content": "2026年1月15日买入沪深300指数基金 2 万。",
        "kind": "episodic",
        "cues": ["2026-01-15", "指数基金"],
    },
    {
        "content": "2026年2月1日开始定投：每周四 1000 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "定投"],
    },
    {
        "content": "2026年2月20日买股票：宁德时代 100 股，成本 210 元。",
        "kind": "episodic",
        "cues": ["2026-02-20", "宁德时代"],
    },
    {
        "content": "2026年3月10日宁德时代跌到 195，没卖。",
        "kind": "episodic",
        "cues": ["2026-03-10", "宁德时代"],
    },
    {
        "content": "2026年3月25日定投调整：每月 4000 元。",
        "kind": "episodic",
        "cues": ["2026-03-25", "定投"],
    },
    {
        "content": "2026年4月10日买可转债：隆22转债 10 张。",
        "kind": "episodic",
        "cues": ["2026-04-10", "可转债"],
    },
    {
        "content": "2026年4月30日卖出可转债：赚 320 元。",
        "kind": "episodic",
        "cues": ["2026-04-30", "可转债"],
    },
    {
        "content": "2026年5月15日指数基金分红：每份 0.08 元。",
        "kind": "episodic",
        "cues": ["2026-05-15", "分红"],
    },
    {
        "content": "2026年6月1日宁德时代涨回 225，卖出 50 股。",
        "kind": "episodic",
        "cues": ["2026-06-01", "宁德时代"],
    },
    {
        "content": "2026年6月20日券商通知：7 月 1 日起佣金调到万1.2。",
        "kind": "episodic",
        "cues": ["2026-06-20", "佣金"],
    },
    {
        "content": "2026年7月1日新佣金生效。",
        "kind": "episodic",
        "cues": ["2026-07-01", "佣金"],
    },
    {
        "content": "2026年7月10日买国债逆回购：10 万，7 天期。",
        "kind": "episodic",
        "cues": ["2026-07-10", "逆回购"],
    },
    {
        "content": "2026年7月15日逆回购收益到账：96 元。",
        "kind": "episodic",
        "cues": ["2026-07-15", "逆回购", "收益"],
    },
    {
        "content": "2026年7月25日收到税务提示：8 月 15 日前报税。",
        "kind": "episodic",
        "cues": ["2026-07-25", "报税"],
    },
    {
        "content": "2026年8月1日账户总资产 32.8 万。",
        "kind": "episodic",
        "cues": ["2026-08-01", "总资产"],
    },
    {
        "content": "2026年8月5日预约 8 月 18 日券商面签。",
        "kind": "episodic",
        "cues": ["2026-08-05", "面签"],
    },
    {
        "content": "基金定投规则：逢跌加仓 10%。",
        "kind": "semantic",
        "cues": ["定投规则"],
    },
    {
        "content": "止损线：个股 -15% 止损。",
        "kind": "semantic",
        "cues": ["止损"],
    },
    {
        "content": "止盈线：基金 +20% 止盈。",
        "kind": "semantic",
        "cues": ["止盈"],
    },
    {
        "content": "券商客服 95588。",
        "kind": "semantic",
        "cues": ["券商", "电话"],
    },
    {
        "content": "股票账户：资金账号 6688-2026。",
        "kind": "semantic",
        "cues": ["资金账号", "6688"],
    },
    {
        "content": "2026年8月8日收到持仓提醒：8 月 12 日宁德时代业绩发布。",
        "kind": "episodic",
        "cues": ["2026-08-08", "业绩"],
    },
    {
        "content": "风险偏好：稳健型，股票仓位不超过 30%。",
        "kind": "semantic",
        "cues": ["风险偏好"],
    },
    {
        "content": "2026年8月9日预约 8 月 16 日理财经理电话。",
        "kind": "episodic",
        "cues": ["2026-08-09", "理财经理"],
    },
]


QUESTIONS = [
    {
        "dim": "开户信息",
        "q": "现在券商佣金是多少？客服电话多少？",
        "answer": "万1.2，95588",
        "terms": ["1.2", "95588"],
    },
    {
        "dim": "定投记录",
        "q": "现在定投金额是多少？",
        "answer": "每月4000元",
        "terms": ["4000"],
    },
    {
        "dim": "股票持仓",
        "q": "宁德时代成本价多少？",
        "answer": "210元",
        "terms": ["210"],
    },
    {
        "dim": "卖出记录",
        "q": "上次卖出可转债是什么时候？赚了多少？",
        "answer": "4月30日，可转债赚320元",
        "terms": ["320"],
    },
    {
        "dim": "未来安排",
        "q": "下次券商面签是什么时候？",
        "answer": "8月18日",
        "terms": ["18"],
    },
    {
        "dim": "收益记录",
        "q": "上次国债逆回购赚了多少？",
        "answer": "96元",
        "terms": ["96"],
    },
    {
        "dim": "税务安排",
        "q": "什么时候报税？",
        "answer": "8月15日前",
        "terms": ["15"],
    },
    {
        "dim": "风控规则",
        "q": "个股止损线是多少？",
        "answer": "-15%",
        "terms": ["15"],
    },
    {
        "dim": "持仓提醒",
        "q": "宁德时代什么时候发业绩？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "资产账户",
        "q": "资金账号多少？",
        "answer": "6688-2026",
        "terms": ["6688"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="投资理财",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="invest_mem0db",
        out_name="invest_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
