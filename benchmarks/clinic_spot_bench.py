"""Community-clinic spot-check (round 361): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月8日第一次去社区诊所，挂号费10元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "挂号"],
    },
    {
        "content": "2026年1月8日看内科，开药48元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "内科"],
    },
    {
        "content": "诊所门诊时间：周一至周六上午8点到12点。",
        "kind": "semantic",
        "cues": ["门诊", "8点"],
    },
    {
        "content": "诊所电话 0771-6666-2222。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "科室：内科、外科、儿科、中医科、检验科。",
        "kind": "semantic",
        "cues": ["科室", "内科"],
    },
    {
        "content": "2026年2月2日预约2月14日复诊。",
        "kind": "episodic",
        "cues": ["2026-02-02", "复诊"],
    },
    {
        "content": "2026年2月14日复诊完成。",
        "kind": "episodic",
        "cues": ["2026-02-14", "复诊"],
    },
    {
        "content": "医保说明：医保卡可报销60%。",
        "kind": "semantic",
        "cues": ["医保", "报销"],
    },
    {
        "content": "2026年3月8日收到通知：3月22日免费体检。",
        "kind": "episodic",
        "cues": ["2026-03-08", "体检"],
    },
    {
        "content": "2026年3月22日免费体检完成。",
        "kind": "episodic",
        "cues": ["2026-03-22", "体检"],
    },
    {
        "content": "2026年4月10日预约4月24日儿科就诊。",
        "kind": "episodic",
        "cues": ["2026-04-10", "儿科"],
    },
    {
        "content": "2026年4月24日儿科就诊完成。",
        "kind": "episodic",
        "cues": ["2026-04-24", "儿科"],
    },
    {
        "content": "2026年5月8日收到通知：5月22日转诊协助。",
        "kind": "episodic",
        "cues": ["2026-05-08", "转诊"],
    },
    {
        "content": "2026年5月22日转诊到区医院完成。",
        "kind": "episodic",
        "cues": ["2026-05-22", "转诊"],
    },
    {
        "content": "2026年6月10日预约6月24日中医科就诊。",
        "kind": "episodic",
        "cues": ["2026-06-10", "中医科"],
    },
    {
        "content": "2026年6月24日中医科就诊完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "中医科"],
    },
    {
        "content": "2026年7月8日收到通知：7月22日夏季防暑讲座。",
        "kind": "episodic",
        "cues": ["2026-07-08", "讲座"],
    },
    {
        "content": "2026年8月3日预约8月16日复诊。",
        "kind": "episodic",
        "cues": ["2026-08-03", "复诊"],
    },
    {
        "content": "2026年8月10日收到提醒：8月24日药品补货。",
        "kind": "episodic",
        "cues": ["2026-08-10", "药品"],
    },
    {
        "content": "2026年8月12日收到通知：8月28日秋季体检。",
        "kind": "episodic",
        "cues": ["2026-08-12", "体检"],
    },
]


QUESTIONS = [
    {
        "dim": "首次就诊",
        "q": "第一次去社区诊所是什么时候？",
        "answer": "1月8日",
        "terms": ["8"],
    },
    {
        "dim": "挂号费",
        "q": "社区诊所挂号费多少？",
        "answer": "10元",
        "terms": ["10"],
    },
    {
        "dim": "下次复诊",
        "q": "下次复诊是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "门诊时间",
        "q": "诊所上午几点开诊？",
        "answer": "8点",
        "terms": ["8"],
    },
    {
        "dim": "电话",
        "q": "诊所电话多少？",
        "answer": "0771-6666-2222",
        "terms": ["2222"],
    },
    {
        "dim": "科室",
        "q": "诊所有哪些科室？",
        "answer": "内科、外科、儿科、中医科、检验科",
        "terms": ["检验科"],
    },
    {
        "dim": "开药费用",
        "q": "第一次开药多少钱？",
        "answer": "48元",
        "terms": ["48"],
    },
    {
        "dim": "医保报销",
        "q": "医保卡报销多少？",
        "answer": "60%",
        "terms": ["60"],
    },
    {
        "dim": "转诊",
        "q": "转诊什么时候完成的？",
        "answer": "5月22日",
        "terms": ["22"],
    },
    {
        "dim": "秋季体检",
        "q": "秋季体检什么时候？",
        "answer": "8月28日",
        "terms": ["28"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="社区诊所",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="clinic_mem0db",
        out_name="clinic_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
