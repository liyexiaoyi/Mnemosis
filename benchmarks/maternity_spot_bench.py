"""Maternity-center spot-check (round 345): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月9日签约月子中心28天套餐，价格39800元。",
        "kind": "episodic",
        "cues": ["2026-01-09", "签约"],
    },
    {
        "content": "2026年1月9日支付定金8000元。",
        "kind": "episodic",
        "cues": ["2026-01-09", "定金"],
    },
    {
        "content": "月子中心电话 0411-8888-7777。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "服务项目：母婴护理、月子餐、产后修复、婴儿游泳。",
        "kind": "semantic",
        "cues": ["服务", "项目"],
    },
    {
        "content": "2026年2月8日收到通知：2月22日孕期讲座。",
        "kind": "episodic",
        "cues": ["2026-02-08", "讲座"],
    },
    {
        "content": "2026年2月22日孕期讲座完成。",
        "kind": "episodic",
        "cues": ["2026-02-22", "讲座"],
    },
    {
        "content": "探视规则：每天下午2点到5点探视。",
        "kind": "semantic",
        "cues": ["探视", "规则"],
    },
    {
        "content": "2026年3月10日预约3月24日参观月子中心。",
        "kind": "episodic",
        "cues": ["2026-03-10", "参观"],
    },
    {
        "content": "2026年3月24日参观完成。",
        "kind": "episodic",
        "cues": ["2026-03-24", "参观"],
    },
    {
        "content": "2026年4月6日收到通知：4月20日护理师见面会。",
        "kind": "episodic",
        "cues": ["2026-04-06", "护理师"],
    },
    {
        "content": "2026年4月20日见面会完成，指定张护理师。",
        "kind": "episodic",
        "cues": ["2026-04-20", "护理师"],
    },
    {
        "content": "退款规则：入住前30天可全额退款。",
        "kind": "semantic",
        "cues": ["退款", "规则"],
    },
    {
        "content": "2026年5月12日收到通知：5月26日月子餐试吃。",
        "kind": "episodic",
        "cues": ["2026-05-12", "试吃"],
    },
    {
        "content": "2026年5月26日试吃完成，选A套餐。",
        "kind": "episodic",
        "cues": ["2026-05-26", "试吃"],
    },
    {
        "content": "2026年6月10日预约6月23日产检陪同服务。",
        "kind": "episodic",
        "cues": ["2026-06-10", "产检"],
    },
    {
        "content": "2026年6月23日产检陪同完成。",
        "kind": "episodic",
        "cues": ["2026-06-23", "产检"],
    },
    {
        "content": "2026年7月8日收到通知：7月24日入住前准备说明会。",
        "kind": "episodic",
        "cues": ["2026-07-08", "说明会"],
    },
    {
        "content": "2026年7月24日说明会完成。",
        "kind": "episodic",
        "cues": ["2026-07-24", "说明会"],
    },
    {
        "content": "2026年8月3日预约8月18日入住。",
        "kind": "episodic",
        "cues": ["2026-08-03", "入住"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日尾款支付。",
        "kind": "episodic",
        "cues": ["2026-08-10", "尾款"],
    },
]


QUESTIONS = [
    {
        "dim": "签约时间",
        "q": "月子中心第一次什么时候签约的？",
        "answer": "1月9日",
        "terms": ["9"],
    },
    {
        "dim": "套餐价格",
        "q": "28天套餐多少钱？",
        "answer": "39800元",
        "terms": ["39800"],
    },
    {
        "dim": "入住时间",
        "q": "下次入住是什么时候？",
        "answer": "8月18日",
        "terms": ["18"],
    },
    {
        "dim": "服务项目",
        "q": "月子中心有哪些服务项目？",
        "answer": "母婴护理、月子餐、产后修复、婴儿游泳",
        "terms": ["产后修复"],
    },
    {
        "dim": "电话",
        "q": "月子中心电话多少？",
        "answer": "0411-8888-7777",
        "terms": ["7777"],
    },
    {
        "dim": "探视规则",
        "q": "每天几点可以探视？",
        "answer": "下午2点到5点",
        "terms": ["2点"],
    },
    {
        "dim": "护理师",
        "q": "指定了哪位护理师？",
        "answer": "张护理师",
        "terms": ["张"],
    },
    {
        "dim": "退款规则",
        "q": "入住前多久可以全额退款？",
        "answer": "30天",
        "terms": ["30"],
    },
    {
        "dim": "尾款支付",
        "q": "尾款什么时候支付？",
        "answer": "8月25日",
        "terms": ["25"],
    },
    {
        "dim": "月子餐",
        "q": "月子餐选了什么套餐？",
        "answer": "A套餐",
        "terms": ["A"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="月子中心",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="maternity_mem0db",
        out_name="maternity_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
