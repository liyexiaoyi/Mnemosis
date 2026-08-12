"""Elderly-care-home spot-check (round 358): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月9日第一次参观养老院，月费4500元。",
        "kind": "episodic",
        "cues": ["2026-01-09", "参观"],
    },
    {
        "content": "2026年1月16日预约1月28日试住。",
        "kind": "episodic",
        "cues": ["2026-01-16", "试住"],
    },
    {
        "content": "2026年1月28日试住完成。",
        "kind": "episodic",
        "cues": ["2026-01-28", "试住"],
    },
    {
        "content": "养老院接待时间：早8点到晚7点。",
        "kind": "semantic",
        "cues": ["接待", "8点"],
    },
    {
        "content": "养老院电话 024-8888-4444。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "服务项目：生活照料、医疗照护、康复训练、文娱活动。",
        "kind": "semantic",
        "cues": ["服务", "项目"],
    },
    {
        "content": "伙食说明：每日三餐两点，可定制软食。",
        "kind": "semantic",
        "cues": ["养老院", "伙食", "三餐"],
    },
    {
        "content": "2026年2月8日收到通知：2月22日家属开放日。",
        "kind": "episodic",
        "cues": ["2026-02-08", "开放日"],
    },
    {
        "content": "2026年2月22日开放日完成。",
        "kind": "episodic",
        "cues": ["2026-02-22", "开放日"],
    },
    {
        "content": "2026年3月10日预约3月24日医疗评估。",
        "kind": "episodic",
        "cues": ["2026-03-10", "评估"],
    },
    {
        "content": "2026年3月24日医疗评估完成。",
        "kind": "episodic",
        "cues": ["2026-03-24", "评估"],
    },
    {
        "content": "2026年4月6日收到通知：4月20日春季文娱活动。",
        "kind": "episodic",
        "cues": ["2026-04-06", "文娱"],
    },
    {
        "content": "2026年4月20日活动完成。",
        "kind": "episodic",
        "cues": ["2026-04-20", "文娱"],
    },
    {
        "content": "押金说明：入住押金5000元，退住退还。",
        "kind": "semantic",
        "cues": ["押金", "说明"],
    },
    {
        "content": "2026年5月8日收到通知：5月22日健康体检。",
        "kind": "episodic",
        "cues": ["2026-05-08", "体检"],
    },
    {
        "content": "2026年5月22日体检完成。",
        "kind": "episodic",
        "cues": ["2026-05-22", "体检"],
    },
    {
        "content": "2026年6月10日预约6月24日再次参观。",
        "kind": "episodic",
        "cues": ["2026-06-10", "参观"],
    },
    {
        "content": "2026年6月24日再次参观完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "参观"],
    },
    {
        "content": "2026年8月4日预约8月17日探视。",
        "kind": "episodic",
        "cues": ["2026-08-04", "探视"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日入住申请截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "申请"],
    },
]


QUESTIONS = [
    {
        "dim": "首次参观",
        "q": "第一次参观养老院是什么时候？",
        "answer": "1月9日",
        "terms": ["9"],
    },
    {
        "dim": "月费",
        "q": "养老院一个月多少钱？",
        "answer": "4500元",
        "terms": ["4500"],
    },
    {
        "dim": "下次探视",
        "q": "下次探视是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "接待时间",
        "q": "养老院几点开门接待？",
        "answer": "早8点",
        "terms": ["8"],
    },
    {
        "dim": "电话",
        "q": "养老院电话多少？",
        "answer": "024-8888-4444",
        "terms": ["4444"],
    },
    {
        "dim": "服务项目",
        "q": "养老院有哪些服务项目？",
        "answer": "生活照料、医疗照护、康复训练、文娱活动",
        "terms": ["康复训练"],
    },
    {
        "dim": "伙食",
        "q": "养老院每天几餐？",
        "answer": "三餐两点",
        "terms": ["三餐"],
    },
    {
        "dim": "押金",
        "q": "入住押金多少钱？",
        "answer": "5000元",
        "terms": ["5000"],
    },
    {
        "dim": "医疗评估",
        "q": "医疗评估什么时候完成的？",
        "answer": "3月24日",
        "terms": ["24"],
    },
    {
        "dim": "申请截止",
        "q": "入住申请什么时候截止？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="养老院咨询",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="elderly_mem0db",
        out_name="elderly_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
