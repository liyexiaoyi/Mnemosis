"""Pet-hospital spot-check (round 349): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月7日第一次带猫咪去宠物医院，挂号费50元。",
        "kind": "episodic",
        "cues": ["2026-01-07", "挂号"],
    },
    {
        "content": "2026年1月7日猫咪体检，诊疗费300元。",
        "kind": "episodic",
        "cues": ["2026-01-07", "体检"],
    },
    {
        "content": "宠物医院营业时间：早8点到晚10点。",
        "kind": "semantic",
        "cues": ["营业时间", "8点"],
    },
    {
        "content": "宠物医院电话 023-6666-8888。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "诊疗项目：体检、绝育、牙科、皮肤科、影像检查。",
        "kind": "semantic",
        "cues": ["项目", "体检"],
    },
    {
        "content": "2026年2月2日预约2月14日猫咪绝育手术。",
        "kind": "episodic",
        "cues": ["2026-02-02", "绝育"],
    },
    {
        "content": "2026年2月14日绝育手术完成，费用1200元。",
        "kind": "episodic",
        "cues": ["2026-02-14", "绝育"],
    },
    {
        "content": "2026年3月5日预约3月18日复诊。",
        "kind": "episodic",
        "cues": ["2026-03-05", "复诊"],
    },
    {
        "content": "2026年3月18日复诊完成，恢复良好。",
        "kind": "episodic",
        "cues": ["2026-03-18", "复诊"],
    },
    {
        "content": "疫苗说明：猫咪每年打一次猫三联。",
        "kind": "semantic",
        "cues": ["疫苗", "猫三联"],
    },
    {
        "content": "2026年4月6日猫咪打猫三联疫苗。",
        "kind": "episodic",
        "cues": ["2026-04-06", "疫苗"],
    },
    {
        "content": "住院规则：住院需提前办理手续。",
        "kind": "semantic",
        "cues": ["住院", "规则"],
    },
    {
        "content": "2026年5月10日预约5月24日皮肤科检查。",
        "kind": "episodic",
        "cues": ["2026-05-10", "皮肤科"],
    },
    {
        "content": "2026年5月24日皮肤科检查完成。",
        "kind": "episodic",
        "cues": ["2026-05-24", "皮肤科"],
    },
    {
        "content": "急诊规则：夜间急诊加收100元。",
        "kind": "semantic",
        "cues": ["急诊", "规则"],
    },
    {
        "content": "2026年6月8日收到通知：6月22日会员日优惠。",
        "kind": "episodic",
        "cues": ["2026-06-08", "会员日"],
    },
    {
        "content": "2026年6月22日会员日诊疗9折。",
        "kind": "episodic",
        "cues": ["2026-06-22", "会员日"],
    },
    {
        "content": "2026年7月9日预约7月23日复诊。",
        "kind": "episodic",
        "cues": ["2026-07-09", "复诊"],
    },
    {
        "content": "2026年8月2日预约8月16日下次复诊。",
        "kind": "episodic",
        "cues": ["2026-08-02", "复诊"],
    },
    {
        "content": "2026年8月10日收到提醒：8月24日猫三联疫苗到期。",
        "kind": "episodic",
        "cues": ["2026-08-10", "疫苗"],
    },
]


QUESTIONS = [
    {
        "dim": "首次就诊",
        "q": "第一次去宠物医院是什么时候？",
        "answer": "1月7日",
        "terms": ["7"],
    },
    {
        "dim": "挂号费",
        "q": "宠物医院挂号费多少？",
        "answer": "50元",
        "terms": ["50"],
    },
    {
        "dim": "下次复诊",
        "q": "下次复诊是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "营业时间",
        "q": "宠物医院几点开门？",
        "answer": "早8点",
        "terms": ["8"],
    },
    {
        "dim": "电话",
        "q": "宠物医院电话多少？",
        "answer": "023-6666-8888",
        "terms": ["8888"],
    },
    {
        "dim": "诊疗项目",
        "q": "医院有哪些诊疗项目？",
        "answer": "体检、绝育、牙科、皮肤科、影像检查",
        "terms": ["绝育"],
    },
    {
        "dim": "绝育费用",
        "q": "绝育手术多少钱？",
        "answer": "1200元",
        "terms": ["1200"],
    },
    {
        "dim": "疫苗",
        "q": "猫咪多久打一次猫三联？",
        "answer": "每年一次",
        "terms": ["每年"],
    },
    {
        "dim": "急诊规则",
        "q": "夜间急诊加收多少钱？",
        "answer": "100元",
        "terms": ["100"],
    },
    {
        "dim": "会员日优惠",
        "q": "会员日诊疗打几折？",
        "answer": "9折",
        "terms": ["9"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="宠物医院",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="pet_hospital_mem0db",
        out_name="pet_hospital_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
