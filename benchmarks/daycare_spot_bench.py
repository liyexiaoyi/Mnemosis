"""Community-daycare spot-check (round 350): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月8日报名社区托育中心，月费2800元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "报名"],
    },
    {
        "content": "2026年1月12日第一次送孩子入托。",
        "kind": "episodic",
        "cues": ["2026-01-12", "入托"],
    },
    {
        "content": "托育中心营业时间：早7点半到晚6点。",
        "kind": "semantic",
        "cues": ["营业时间", "7点半"],
    },
    {
        "content": "托育中心电话 0510-6666-9999。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "托育内容：早教游戏、绘本阅读、手工、户外活动。",
        "kind": "semantic",
        "cues": ["内容", "绘本"],
    },
    {
        "content": "餐食说明：含两餐两点，可定制过敏餐。",
        "kind": "semantic",
        "cues": ["托育中心", "餐食", "两餐"],
    },
    {
        "content": "2026年2月3日收到通知：2月17日家长会。",
        "kind": "episodic",
        "cues": ["2026-02-03", "家长会"],
    },
    {
        "content": "2026年2月17日家长会完成。",
        "kind": "episodic",
        "cues": ["2026-02-17", "家长会"],
    },
    {
        "content": "安全规则：接送需凭接送卡。",
        "kind": "semantic",
        "cues": ["安全", "接送卡"],
    },
    {
        "content": "2026年3月10日预约3月24日观摩课。",
        "kind": "episodic",
        "cues": ["2026-03-10", "观摩课"],
    },
    {
        "content": "2026年3月24日观摩课完成。",
        "kind": "episodic",
        "cues": ["2026-03-24", "观摩课"],
    },
    {
        "content": "2026年4月6日收到通知：4月20日春季亲子活动。",
        "kind": "episodic",
        "cues": ["2026-04-06", "亲子活动"],
    },
    {
        "content": "2026年4月20日亲子活动完成。",
        "kind": "episodic",
        "cues": ["2026-04-20", "亲子活动"],
    },
    {
        "content": "退费规则：提前15天申请可退当月费用。",
        "kind": "semantic",
        "cues": ["退费", "规则"],
    },
    {
        "content": "2026年5月8日收到通知：5月22日托育开放日。",
        "kind": "episodic",
        "cues": ["2026-05-08", "开放日"],
    },
    {
        "content": "2026年5月22日开放日完成。",
        "kind": "episodic",
        "cues": ["2026-05-22", "开放日"],
    },
    {
        "content": "2026年6月10日预约6月24日入园评估。",
        "kind": "episodic",
        "cues": ["2026-06-10", "评估"],
    },
    {
        "content": "2026年6月24日入园评估完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "评估"],
    },
    {
        "content": "2026年8月3日预约8月17日入托。",
        "kind": "episodic",
        "cues": ["2026-08-03", "入托"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日月费缴纳。",
        "kind": "episodic",
        "cues": ["2026-08-10", "月费"],
    },
]


QUESTIONS = [
    {
        "dim": "报名时间",
        "q": "托育中心第一次什么时候报名的？",
        "answer": "1月8日",
        "terms": ["8"],
    },
    {
        "dim": "月费",
        "q": "托育一个月多少钱？",
        "answer": "2800元",
        "terms": ["2800"],
    },
    {
        "dim": "下次入托",
        "q": "下次入托是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "托育中心几点开门？",
        "answer": "早7点半",
        "terms": ["7点半"],
    },
    {
        "dim": "电话",
        "q": "托育中心电话多少？",
        "answer": "0510-6666-9999",
        "terms": ["9999"],
    },
    {
        "dim": "托育内容",
        "q": "托育中心有哪些内容？",
        "answer": "早教游戏、绘本阅读、手工、户外活动",
        "terms": ["绘本"],
    },
    {
        "dim": "餐食",
        "q": "托育中心含几餐？",
        "answer": "两餐两点",
        "terms": ["两餐"],
    },
    {
        "dim": "安全规则",
        "q": "接送孩子需要什么？",
        "answer": "接送卡",
        "terms": ["接送卡"],
    },
    {
        "dim": "退费规则",
        "q": "退当月费用要提前几天申请？",
        "answer": "15天",
        "terms": ["15"],
    },
    {
        "dim": "月费缴纳",
        "q": "月费什么时候缴纳？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="社区托育中心",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="daycare_mem0db",
        out_name="daycare_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
