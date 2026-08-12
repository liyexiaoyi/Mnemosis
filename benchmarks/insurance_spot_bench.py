"""Insurance-claims spot-check (round 289): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买重疾险：50 万保额，年缴 6800。",
        "kind": "episodic",
        "cues": ["2026-01-10", "重疾险"],
    },
    {
        "content": "2026年2月1日买医疗险：百万医疗。",
        "kind": "episodic",
        "cues": ["2026-02-01", "医疗险"],
    },
    {
        "content": "2026年3月15日感冒住院，申请理赔。",
        "kind": "episodic",
        "cues": ["2026-03-15", "理赔"],
    },
    {
        "content": "2026年4月1日理赔到账 3200 元。",
        "kind": "episodic",
        "cues": ["2026-04-01", "理赔"],
    },
    {
        "content": "2026年5月10日保单体检：5 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-05-10", "体检"],
    },
    {
        "content": "2026年5月20日保单体检完成。",
        "kind": "episodic",
        "cues": ["2026-05-20", "体检"],
    },
    {
        "content": "2026年6月1日续缴重疾险保费。",
        "kind": "episodic",
        "cues": ["2026-06-01", "续缴"],
    },
    {
        "content": "2026年6月20日收到提醒：6 月 30 日前补充材料。",
        "kind": "episodic",
        "cues": ["2026-06-20", "补充"],
    },
    {
        "content": "2026年6月30日补材料完成。",
        "kind": "episodic",
        "cues": ["2026-06-30", "补充"],
    },
    {
        "content": "2026年7月10日预约 7 月 20 日理赔面谈。",
        "kind": "episodic",
        "cues": ["2026-07-10", "面谈"],
    },
    {
        "content": "2026年7月20日面谈完成。",
        "kind": "episodic",
        "cues": ["2026-07-20", "面谈"],
    },
    {
        "content": "2026年8月1日收到理赔审核：8 月 15 日结果。",
        "kind": "episodic",
        "cues": ["2026-08-01", "审核"],
    },
    {
        "content": "2026年8月5日理赔客服回访。",
        "kind": "episodic",
        "cues": ["2026-08-05", "回访"],
    },
    {
        "content": "保单号 P-2026-0315。",
        "kind": "semantic",
        "cues": ["保单号", "P-2026-0315"],
    },
    {
        "content": "保险公司客服 95599。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日续保优惠。",
        "kind": "episodic",
        "cues": ["2026-08-08", "续保"],
    },
    {
        "content": "理赔材料清单：发票、病历、诊断证明。",
        "kind": "semantic",
        "cues": ["理赔材料"],
    },
    {
        "content": "2026年8月9日预约 8 月 18 日递交补充材料。",
        "kind": "episodic",
        "cues": ["2026-08-09", "递交"],
    },
]


QUESTIONS = [
    {
        "dim": "保险配置",
        "q": "重疾险保额多少？一年多少钱？",
        "answer": "50万，6800元",
        "terms": ["50", "6800"],
    },
    {
        "dim": "理赔记录",
        "q": "上次理赔到账多少？",
        "answer": "3200元",
        "terms": ["3200"],
    },
    {
        "dim": "理赔进度",
        "q": "理赔审核结果什么时候出？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "未来安排",
        "q": "下次递交材料是什么时候？",
        "answer": "8月18日",
        "terms": ["18"],
    },
    {
        "dim": "理赔材料",
        "q": "理赔要交什么材料？",
        "answer": "发票、病历、诊断证明",
        "terms": ["诊断证明"],
    },
    {
        "dim": "保单信息",
        "q": "保单号多少？",
        "answer": "P-2026-0315",
        "terms": ["P"],
    },
    {
        "dim": "客服电话",
        "q": "保险公司客服电话多少？",
        "answer": "95599",
        "terms": ["95599"],
    },
    {
        "dim": "续费记录",
        "q": "重疾险什么时候续缴的？",
        "answer": "6月1日",
        "terms": ["1"],
    },
    {
        "dim": "补充材料",
        "q": "什么时候补充材料？",
        "answer": "6月30日前",
        "terms": ["30"],
    },
    {
        "dim": "面谈记录",
        "q": "上次理赔面谈是什么时候？",
        "answer": "7月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="保险理赔",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="insurance_mem0db",
        out_name="insurance_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
