"""TCM-clinic spot-check (round 335): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月7日在中医馆挂第一次号。",
        "kind": "episodic",
        "cues": ["2026-01-07", "挂号"],
    },
    {
        "content": "2026年1月7日看诊王医生，开中药7副，药费320元。",
        "kind": "episodic",
        "cues": ["2026-01-07", "中药"],
    },
    {
        "content": "中医馆坐诊时间：每周三、周日上午。",
        "kind": "semantic",
        "cues": ["坐诊", "周三"],
    },
    {
        "content": "2026年2月1日预约2月14日复诊。",
        "kind": "episodic",
        "cues": ["2026-02-01", "复诊"],
    },
    {
        "content": "2026年2月14日复诊完成，改为每两周一次。",
        "kind": "episodic",
        "cues": ["2026-02-14", "复诊"],
    },
    {
        "content": "中医馆前台电话 028-7777-3333。",
        "kind": "semantic",
        "cues": ["前台", "电话"],
    },
    {
        "content": "医保报销规则：中药费报销70%。",
        "kind": "semantic",
        "cues": ["医保", "报销"],
    },
    {
        "content": "2026年3月8日收到通知：3月21日中医馆春季义诊。",
        "kind": "episodic",
        "cues": ["2026-03-08", "义诊"],
    },
    {
        "content": "2026年3月21日义诊完成，免费测血压。",
        "kind": "episodic",
        "cues": ["2026-03-21", "义诊"],
    },
    {
        "content": "2026年4月5日预约4月19日复诊。",
        "kind": "episodic",
        "cues": ["2026-04-05", "复诊"],
    },
    {
        "content": "2026年4月19日复诊完成，开了调理方。",
        "kind": "episodic",
        "cues": ["2026-04-19", "复诊"],
    },
    {
        "content": "2026年5月6日办理中医馆会员卡，充值1000元。",
        "kind": "episodic",
        "cues": ["2026-05-06", "会员卡"],
    },
    {
        "content": "2026年5月15日购买艾灸套餐，费用260元。",
        "kind": "episodic",
        "cues": ["2026-05-15", "艾灸"],
    },
    {
        "content": "2026年6月10日收到通知：6月24日冬病夏治三伏贴预约。",
        "kind": "episodic",
        "cues": ["2026-06-10", "三伏贴"],
    },
    {
        "content": "2026年6月24日预约7月12日三伏贴。",
        "kind": "episodic",
        "cues": ["2026-06-24", "三伏贴"],
    },
    {
        "content": "2026年7月12日三伏贴完成。",
        "kind": "episodic",
        "cues": ["2026-07-12", "三伏贴"],
    },
    {
        "content": "2026年7月25日预约8月9日复诊。",
        "kind": "episodic",
        "cues": ["2026-07-25", "复诊"],
    },
    {
        "content": "2026年8月6日收到提醒：8月20日会员卡余额不足。",
        "kind": "episodic",
        "cues": ["2026-08-06", "余额"],
    },
    {
        "content": "2026年8月10日收到通知：8月24日秋季养生讲座。",
        "kind": "episodic",
        "cues": ["2026-08-10", "讲座"],
    },
    {
        "content": "煎药服务：可代煎，需提前一天送药。",
        "kind": "semantic",
        "cues": ["煎药", "服务"],
    },
]


QUESTIONS = [
    {
        "dim": "首次挂号",
        "q": "中医馆第一次挂号是什么时候？",
        "answer": "1月7日",
        "terms": ["7"],
    },
    {
        "dim": "药费",
        "q": "第一次开的中药多少钱？",
        "answer": "320元",
        "terms": ["320"],
    },
    {
        "dim": "下次复诊",
        "q": "下次复诊是什么时候？",
        "answer": "8月9日",
        "terms": ["9"],
    },
    {
        "dim": "坐诊时间",
        "q": "中医馆每周几坐诊？",
        "answer": "周三、周日上午",
        "terms": ["周三"],
    },
    {
        "dim": "前台电话",
        "q": "中医馆前台电话多少？",
        "answer": "028-7777-3333",
        "terms": ["3333"],
    },
    {
        "dim": "医保报销",
        "q": "中药费医保报销多少？",
        "answer": "70%",
        "terms": ["70"],
    },
    {
        "dim": "三伏贴",
        "q": "三伏贴什么时候贴的？",
        "answer": "7月12日",
        "terms": ["12"],
    },
    {
        "dim": "养生讲座",
        "q": "秋季养生讲座什么时候？",
        "answer": "8月24日",
        "terms": ["24"],
    },
    {
        "dim": "煎药服务",
        "q": "代煎药需要提前多久送药？",
        "answer": "提前一天",
        "terms": ["一天"],
    },
    {
        "dim": "会员余额",
        "q": "会员卡余额什么时候会不足？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="中医馆",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="tcm_mem0db",
        out_name="tcm_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
