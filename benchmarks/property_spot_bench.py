"""Property-management spot-check (round 357): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月6日第一次缴纳物业费，一年2400元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "物业费"],
    },
    {
        "content": "2026年1月10日预约1月18日水管维修。",
        "kind": "episodic",
        "cues": ["2026-01-10", "维修"],
    },
    {
        "content": "2026年1月18日水管维修完成。",
        "kind": "episodic",
        "cues": ["2026-01-18", "维修"],
    },
    {
        "content": "物业服务中心营业时间：早8点到晚6点。",
        "kind": "semantic",
        "cues": ["营业时间", "8点"],
    },
    {
        "content": "物业电话 0851-6666-3333。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "服务项目：维修、保洁、绿化、安保、快递代收。",
        "kind": "semantic",
        "cues": ["服务", "项目"],
    },
    {
        "content": "2026年2月8日收到通知：2月22日小区元宵活动。",
        "kind": "episodic",
        "cues": ["2026-02-08", "元宵"],
    },
    {
        "content": "2026年2月22日元宵活动完成。",
        "kind": "episodic",
        "cues": ["2026-02-22", "元宵"],
    },
    {
        "content": "停车费规则：月租300元。",
        "kind": "semantic",
        "cues": ["停车费", "月租"],
    },
    {
        "content": "投诉渠道：物业前台或400热线。",
        "kind": "semantic",
        "cues": ["投诉", "渠道"],
    },
    {
        "content": "公共设施：游泳池、儿童乐园、健身房。",
        "kind": "semantic",
        "cues": ["公共设施", "游泳池"],
    },
    {
        "content": "2026年3月10日预约3月22日空调维修。",
        "kind": "episodic",
        "cues": ["2026-03-10", "空调"],
    },
    {
        "content": "2026年3月22日空调维修完成。",
        "kind": "episodic",
        "cues": ["2026-03-22", "空调"],
    },
    {
        "content": "2026年4月8日收到通知：4月22日电梯年检。",
        "kind": "episodic",
        "cues": ["2026-04-08", "电梯"],
    },
    {
        "content": "2026年4月22日电梯年检完成。",
        "kind": "episodic",
        "cues": ["2026-04-22", "电梯"],
    },
    {
        "content": "2026年5月10日预约5月24日门锁维修。",
        "kind": "episodic",
        "cues": ["2026-05-10", "门锁"],
    },
    {
        "content": "2026年5月24日门锁维修完成。",
        "kind": "episodic",
        "cues": ["2026-05-24", "门锁"],
    },
    {
        "content": "2026年6月8日收到通知：6月22日夏季灭蚊活动。",
        "kind": "episodic",
        "cues": ["2026-06-08", "灭蚊"],
    },
    {
        "content": "2026年8月3日预约8月16日下水道疏通。",
        "kind": "episodic",
        "cues": ["2026-08-03", "疏通"],
    },
    {
        "content": "2026年8月10日收到提醒：8月24日物业费补缴。",
        "kind": "episodic",
        "cues": ["2026-08-10", "补缴"],
    },
]


QUESTIONS = [
    {
        "dim": "首次缴费",
        "q": "物业费第一次什么时候交的？",
        "answer": "1月6日",
        "terms": ["6"],
    },
    {
        "dim": "物业费",
        "q": "物业费一年多少钱？",
        "answer": "2400元",
        "terms": ["2400"],
    },
    {
        "dim": "下次维修",
        "q": "下次物业维修是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "营业时间",
        "q": "物业服务中心几点开门？",
        "answer": "早8点",
        "terms": ["8"],
    },
    {
        "dim": "电话",
        "q": "物业电话多少？",
        "answer": "0851-6666-3333",
        "terms": ["3333"],
    },
    {
        "dim": "服务项目",
        "q": "物业有哪些服务项目？",
        "answer": "维修、保洁、绿化、安保、快递代收",
        "terms": ["快递代收"],
    },
    {
        "dim": "停车费",
        "q": "停车月租多少钱？",
        "answer": "300元",
        "terms": ["300"],
    },
    {
        "dim": "投诉渠道",
        "q": "物业投诉找哪里？",
        "answer": "前台或400热线",
        "terms": ["400"],
    },
    {
        "dim": "公共设施",
        "q": "小区有哪些公共设施？",
        "answer": "游泳池、儿童乐园、健身房",
        "terms": ["游泳池"],
    },
    {
        "dim": "物业费补缴",
        "q": "物业费什么时候补缴？",
        "answer": "8月24日",
        "terms": ["24"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="小区物业",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="property_mem0db",
        out_name="property_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
