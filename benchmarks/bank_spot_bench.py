"""Bank-counter spot-check (round 308): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日开储蓄卡。",
        "kind": "episodic",
        "cues": ["2026-01-10", "储蓄卡"],
    },
    {
        "content": "2026年1月20日办网银。",
        "kind": "episodic",
        "cues": ["2026-01-20", "网银"],
    },
    {
        "content": "2026年2月1日定期存款：10 万，1 年。",
        "kind": "semantic",
        "cues": ["定期", "10万"],
    },
    {
        "content": "2026年2月15日预约 2 月 25 日换卡。",
        "kind": "episodic",
        "cues": ["2026-02-15", "换卡"],
    },
    {
        "content": "2026年2月25日换卡完成。",
        "kind": "episodic",
        "cues": ["2026-02-25", "换卡"],
    },
    {
        "content": "2026年3月1日汇款：给爸妈 2 万。",
        "kind": "episodic",
        "cues": ["2026-03-01", "汇款"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日理财咨询。",
        "kind": "episodic",
        "cues": ["2026-03-15", "理财"],
    },
    {
        "content": "2026年3月25日咨询完成。",
        "kind": "episodic",
        "cues": ["2026-03-25", "理财"],
    },
    {
        "content": "2026年4月1日开通短信通知。",
        "kind": "episodic",
        "cues": ["2026-04-01", "短信通知"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日打印流水。",
        "kind": "episodic",
        "cues": ["2026-04-15", "流水"],
    },
    {
        "content": "2026年4月25日打印流水完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "流水"],
    },
    {
        "content": "2026年5月1日存钱：5 万。",
        "kind": "episodic",
        "cues": ["2026-05-01", "存钱"],
    },
    {
        "content": "2026年5月20日预约 5 月 30 日改预留手机号。",
        "kind": "episodic",
        "cues": ["2026-05-20", "手机号"],
    },
    {
        "content": "2026年5月30日改手机号完成。",
        "kind": "episodic",
        "cues": ["2026-05-30", "手机号"],
    },
    {
        "content": "2026年6月1日定期到期：6 月 15 日。",
        "kind": "episodic",
        "cues": ["2026-06-01", "到期"],
    },
    {
        "content": "2026年6月15日转存。",
        "kind": "episodic",
        "cues": ["2026-06-15", "转存"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日办信用卡。",
        "kind": "episodic",
        "cues": ["2026-08-01", "信用卡"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日还信用卡。",
        "kind": "episodic",
        "cues": ["2026-08-05", "还款"],
    },
    {
        "content": "银行客服 95566。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "网点地址：中山西路 88 号。",
        "kind": "semantic",
        "cues": ["网点", "地址"],
    },
]


QUESTIONS = [
    {
        "dim": "定期存款",
        "q": "定期存款多少钱？存多久？",
        "answer": "10万，1年",
        "terms": ["10"],
    },
    {
        "dim": "换卡记录",
        "q": "卡什么时候换的？",
        "answer": "2月25日",
        "terms": ["25"],
    },
    {
        "dim": "汇款记录",
        "q": "给爸妈汇了多少钱？",
        "answer": "2万",
        "terms": ["2"],
    },
    {
        "dim": "未来安排",
        "q": "下次办信用卡是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "打印流水",
        "q": "流水什么时候打印的？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "定期到期",
        "q": "定期什么时候到期？",
        "answer": "6月15日",
        "terms": ["15"],
    },
    {
        "dim": "银行客服",
        "q": "银行客服电话多少？",
        "answer": "95566",
        "terms": ["95566"],
    },
    {
        "dim": "网点地址",
        "q": "网点在哪？",
        "answer": "中山西路88号",
        "terms": ["中山西路"],
    },
    {
        "dim": "还款提醒",
        "q": "信用卡什么时候还？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "银行服务",
        "q": "开通了什么服务？",
        "answer": "网银、短信通知",
        "terms": ["短信通知"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="银行柜台",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="bank_mem0db",
        out_name="bank_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
