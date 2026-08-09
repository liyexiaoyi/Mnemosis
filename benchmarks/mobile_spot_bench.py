"""Mobile-plan spot-check (round 288): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日办手机套餐：59 元/月，20G 流量。",
        "kind": "episodic",
        "cues": ["2026-01-10", "套餐"],
    },
    {
        "content": "2026年1月20日携号转网完成。",
        "kind": "episodic",
        "cues": ["2026-01-20", "转网"],
    },
    {
        "content": "2026年2月1日套餐升级：89 元/月，60G。",
        "kind": "episodic",
        "cues": ["2026-02-01", "升级"],
    },
    {
        "content": "2026年2月15日收到账单：2 月 5 日出账。",
        "kind": "episodic",
        "cues": ["2026-02-15", "出账"],
    },
    {
        "content": "2026年3月1日流量超了，买 10 元加油包。",
        "kind": "episodic",
        "cues": ["2026-03-01", "加油包"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日换 5G 套餐。",
        "kind": "episodic",
        "cues": ["2026-03-15", "5G"],
    },
    {
        "content": "2026年3月25日换 5G 套餐：129 元/月。",
        "kind": "episodic",
        "cues": ["2026-03-25", "5G"],
    },
    {
        "content": "2026年4月10日宽带融合：+30 元/月。",
        "kind": "episodic",
        "cues": ["2026-04-10", "宽带"],
    },
    {
        "content": "2026年5月1日5G 信号差，投诉。",
        "kind": "episodic",
        "cues": ["2026-05-01", "投诉"],
    },
    {
        "content": "2026年5月10日客服回访：5 月 15 日上门测信号。",
        "kind": "episodic",
        "cues": ["2026-05-10", "回访"],
    },
    {
        "content": "2026年5月15日上门测信号，建议换路由器。",
        "kind": "episodic",
        "cues": ["2026-05-15", "信号"],
    },
    {
        "content": "2026年6月1日换路由器，信号问题解决。",
        "kind": "episodic",
        "cues": ["2026-06-01", "路由器"],
    },
    {
        "content": "2026年6月15日收到提醒：6 月 20 日套餐到期。",
        "kind": "episodic",
        "cues": ["2026-06-15", "到期"],
    },
    {
        "content": "2026年6月20日续套餐。",
        "kind": "episodic",
        "cues": ["2026-06-20", "续费"],
    },
    {
        "content": "2026年7月1日副卡：给家人办了一张。",
        "kind": "episodic",
        "cues": ["2026-07-01", "副卡"],
    },
    {
        "content": "2026年7月15日话费充 200 送 20。",
        "kind": "episodic",
        "cues": ["2026-07-15", "充值"],
    },
    {
        "content": "2026年8月1日预约 8 月 10 日改套餐。",
        "kind": "episodic",
        "cues": ["2026-08-01", "改套餐"],
    },
    {
        "content": "2026年8月5日收到通知：8 月 20 日 5G 升级活动。",
        "kind": "episodic",
        "cues": ["2026-08-05", "升级活动"],
    },
    {
        "content": "客服电话 10086。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "服务密码 223344。",
        "kind": "semantic",
        "cues": ["服务密码"],
    },
    {
        "content": "2026年8月8日收到提醒：8 月 15 日话费不足。",
        "kind": "episodic",
        "cues": ["2026-08-08", "话费"],
    },
]


QUESTIONS = [
    {
        "dim": "套餐信息",
        "q": "现在什么套餐？多少钱？",
        "answer": "5G套餐，129元/月",
        "terms": ["129"],
    },
    {
        "dim": "出账日期",
        "q": "话费什么时候出账？",
        "answer": "每月5日",
        "terms": ["5"],
    },
    {
        "dim": "流量处理",
        "q": "流量超了怎么办？",
        "answer": "买10元加油包",
        "terms": ["加油包"],
    },
    {
        "dim": "信号问题",
        "q": "5G信号问题怎么解决的？",
        "answer": "换路由器",
        "terms": ["路由器"],
    },
    {
        "dim": "未来安排",
        "q": "下次改套餐是什么时候？",
        "answer": "8月10日",
        "terms": ["10"],
    },
    {
        "dim": "副卡信息",
        "q": "副卡给谁办的？",
        "answer": "家人",
        "terms": ["家人"],
    },
    {
        "dim": "充值优惠",
        "q": "充 200 送多少？",
        "answer": "送20",
        "terms": ["20"],
    },
    {
        "dim": "客服信息",
        "q": "客服电话多少？服务密码呢？",
        "answer": "10086，223344",
        "terms": ["10086", "223344"],
    },
    {
        "dim": "话费提醒",
        "q": "话费什么时候不足？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "升级活动",
        "q": "5G升级活动什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="手机通信",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="mobile_mem0db",
        out_name="mobile_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
