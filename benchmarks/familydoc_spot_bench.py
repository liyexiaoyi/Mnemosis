"""Family-doctor spot-check (round 351): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月8日签约家庭医生，年费600元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "签约"],
    },
    {
        "content": "2026年1月15日第一次家庭医生上门随访。",
        "kind": "episodic",
        "cues": ["2026-01-15", "随访"],
    },
    {
        "content": "家庭医生门诊时间：每周二、周五下午。",
        "kind": "semantic",
        "cues": ["门诊", "周二"],
    },
    {
        "content": "家庭医生电话 020-7777-3333。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "服务内容：健康咨询、慢病管理、用药指导、转诊协助。",
        "kind": "semantic",
        "cues": ["服务", "内容"],
    },
    {
        "content": "2026年2月10日收到通知：2月24日用药指导。",
        "kind": "episodic",
        "cues": ["2026-02-10", "用药"],
    },
    {
        "content": "2026年2月24日用药指导完成。",
        "kind": "episodic",
        "cues": ["2026-02-24", "用药"],
    },
    {
        "content": "2026年3月8日建立健康档案。",
        "kind": "episodic",
        "cues": ["2026-03-08", "健康档案"],
    },
    {
        "content": "2026年3月15日收到通知：3月28日转诊协助。",
        "kind": "episodic",
        "cues": ["2026-03-15", "转诊"],
    },
    {
        "content": "2026年3月28日转诊到市医院完成。",
        "kind": "episodic",
        "cues": ["2026-03-28", "转诊"],
    },
    {
        "content": "2026年4月10日收到通知：4月24日健康讲座。",
        "kind": "episodic",
        "cues": ["2026-04-10", "讲座"],
    },
    {
        "content": "2026年4月24日健康讲座完成。",
        "kind": "episodic",
        "cues": ["2026-04-24", "讲座"],
    },
    {
        "content": "2026年5月6日预约5月20日随访。",
        "kind": "episodic",
        "cues": ["2026-05-06", "随访"],
    },
    {
        "content": "2026年5月20日随访完成。",
        "kind": "episodic",
        "cues": ["2026-05-20", "随访"],
    },
    {
        "content": "2026年6月10日收到通知：6月24日慢病管理评估。",
        "kind": "episodic",
        "cues": ["2026-06-10", "慢病"],
    },
    {
        "content": "2026年6月24日慢病评估完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "慢病"],
    },
    {
        "content": "2026年7月8日预约7月22日随访。",
        "kind": "episodic",
        "cues": ["2026-07-08", "随访"],
    },
    {
        "content": "2026年7月22日随访完成。",
        "kind": "episodic",
        "cues": ["2026-07-22", "随访"],
    },
    {
        "content": "2026年8月3日预约8月16日下次随访。",
        "kind": "episodic",
        "cues": ["2026-08-03", "随访"],
    },
    {
        "content": "2026年8月10日收到提醒：8月24日年费续缴。",
        "kind": "episodic",
        "cues": ["2026-08-10", "续缴"],
    },
]


QUESTIONS = [
    {
        "dim": "签约时间",
        "q": "家庭医生第一次什么时候签约的？",
        "answer": "1月8日",
        "terms": ["8"],
    },
    {
        "dim": "年费",
        "q": "家庭医生一年多少钱？",
        "answer": "600元",
        "terms": ["600"],
    },
    {
        "dim": "下次随访",
        "q": "下次随访是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "门诊时间",
        "q": "家庭医生每周几门诊？",
        "answer": "周二、周五下午",
        "terms": ["周二"],
    },
    {
        "dim": "电话",
        "q": "家庭医生电话多少？",
        "answer": "020-7777-3333",
        "terms": ["3333"],
    },
    {
        "dim": "服务内容",
        "q": "家庭医生有哪些服务内容？",
        "answer": "健康咨询、慢病管理、用药指导、转诊协助",
        "terms": ["慢病管理"],
    },
    {
        "dim": "健康档案",
        "q": "健康档案什么时候建立的？",
        "answer": "3月8日",
        "terms": ["8"],
    },
    {
        "dim": "转诊",
        "q": "转诊什么时候完成的？",
        "answer": "3月28日",
        "terms": ["28"],
    },
    {
        "dim": "慢病评估",
        "q": "慢病管理评估什么时候？",
        "answer": "6月24日",
        "terms": ["24"],
    },
    {
        "dim": "年费续缴",
        "q": "年费什么时候续缴？",
        "answer": "8月24日",
        "terms": ["24"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭医生签约",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="familydoc_mem0db",
        out_name="familydoc_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
