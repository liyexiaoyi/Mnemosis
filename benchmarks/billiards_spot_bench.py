"""Billiards-hall spot-check (round 362): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月6日第一次去台球厅，办会员卡充值300元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "会员卡"],
    },
    {
        "content": "2026年1月10日第一次打球，台费每小时40元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "台费"],
    },
    {
        "content": "台球厅营业时间：早10点到凌晨2点。",
        "kind": "semantic",
        "cues": ["营业时间", "10点"],
    },
    {
        "content": "台球厅电话 0452-6666-3333。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "设施：美式台球桌8张、斯诺克桌2张、休息区、饮品吧。",
        "kind": "semantic",
        "cues": ["设施", "斯诺克"],
    },
    {
        "content": "2026年2月3日预约2月15日斯诺克桌。",
        "kind": "episodic",
        "cues": ["2026-02-03", "斯诺克"],
    },
    {
        "content": "2026年2月15日斯诺克打球完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "斯诺克"],
    },
    {
        "content": "2026年3月8日收到通知：3月22日台球比赛。",
        "kind": "episodic",
        "cues": ["2026-03-08", "比赛"],
    },
    {
        "content": "2026年3月22日比赛完成，获得四强。",
        "kind": "episodic",
        "cues": ["2026-03-22", "比赛"],
    },
    {
        "content": "教练服务：每小时150元，可预约。",
        "kind": "semantic",
        "cues": ["教练", "150元"],
    },
    {
        "content": "2026年4月10日预约4月24日教练课。",
        "kind": "episodic",
        "cues": ["2026-04-10", "教练课"],
    },
    {
        "content": "2026年4月24日教练课完成。",
        "kind": "episodic",
        "cues": ["2026-04-24", "教练课"],
    },
    {
        "content": "会员优惠：会员台费8折。",
        "kind": "semantic",
        "cues": ["会员", "优惠"],
    },
    {
        "content": "2026年5月8日收到通知：5月22日会员日活动。",
        "kind": "episodic",
        "cues": ["2026-05-08", "会员日"],
    },
    {
        "content": "2026年5月22日会员日活动完成。",
        "kind": "episodic",
        "cues": ["2026-05-22", "会员日"],
    },
    {
        "content": "2026年6月10日预约6月24日周末场。",
        "kind": "episodic",
        "cues": ["2026-06-10", "周末场"],
    },
    {
        "content": "2026年6月24日周末场完成。",
        "kind": "episodic",
        "cues": ["2026-06-24", "周末场"],
    },
    {
        "content": "2026年7月8日收到通知：7月22日夏季联赛。",
        "kind": "episodic",
        "cues": ["2026-07-08", "联赛"],
    },
    {
        "content": "2026年8月4日预约8月17日下次打球。",
        "kind": "episodic",
        "cues": ["2026-08-04", "打球"],
    },
    {
        "content": "2026年8月10日收到提醒：8月26日会员卡余额不足。",
        "kind": "episodic",
        "cues": ["2026-08-10", "余额"],
    },
]


QUESTIONS = [
    {
        "dim": "首次办卡",
        "q": "台球厅会员卡第一次什么时候办的？",
        "answer": "1月6日",
        "terms": ["6"],
    },
    {
        "dim": "台费",
        "q": "台费每小时多少钱？",
        "answer": "40元",
        "terms": ["40"],
    },
    {
        "dim": "下次打球",
        "q": "下次打球是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "台球厅几点开门？",
        "answer": "早10点",
        "terms": ["10"],
    },
    {
        "dim": "电话",
        "q": "台球厅电话多少？",
        "answer": "0452-6666-3333",
        "terms": ["3333"],
    },
    {
        "dim": "设施",
        "q": "台球厅有哪些设施？",
        "answer": "美式台球桌8张、斯诺克桌2张、休息区、饮品吧",
        "terms": ["饮品吧"],
    },
    {
        "dim": "教练费用",
        "q": "教练课每小时多少钱？",
        "answer": "150元",
        "terms": ["150"],
    },
    {
        "dim": "会员优惠",
        "q": "会员台费打几折？",
        "answer": "8折",
        "terms": ["8"],
    },
    {
        "dim": "比赛结果",
        "q": "台球比赛结果是什么？",
        "answer": "四强",
        "terms": ["四强"],
    },
    {
        "dim": "余额提醒",
        "q": "会员卡余额什么时候会不足？",
        "answer": "8月26日",
        "terms": ["26"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="台球厅会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="billiards_mem0db",
        out_name="billiards_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
