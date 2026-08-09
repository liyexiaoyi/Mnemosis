"""Car-maintenance spot-check (round 272): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月15日提车：比亚迪海豹，落地 18.6 万。",
        "kind": "episodic",
        "cues": ["2026-01-15", "海豹"],
    },
    {
        "content": "2026年1月20日第一次加油 320 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "加油"],
    },
    {
        "content": "2026年2月10日装行车记录仪 599 元。",
        "kind": "episodic",
        "cues": ["2026-02-10", "记录仪"],
    },
    {
        "content": "2026年2月25日首保预约：3 月 5 日。",
        "kind": "episodic",
        "cues": ["2026-02-25", "首保"],
    },
    {
        "content": "2026年3月5日首保完成：里程 3200km。",
        "kind": "episodic",
        "cues": ["2026-03-05", "首保"],
    },
    {
        "content": "2026年3月15日轮胎扎钉，3 月 18 日补胎 80 元。",
        "kind": "episodic",
        "cues": ["2026-03-15", "补胎"],
    },
    {
        "content": "2026年4月1日保险续费：交强险+商业险 5200 元。",
        "kind": "episodic",
        "cues": ["2026-04-01", "保险"],
    },
    {
        "content": "2026年4月10日二保预约：4 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-04-10", "二保"],
    },
    {
        "content": "2026年4月20日二保完成：换机油机滤，里程 8300km。",
        "kind": "episodic",
        "cues": ["2026-04-20", "二保"],
    },
    {
        "content": "2026年5月1日洗车卡：200 元 10 次。",
        "kind": "episodic",
        "cues": ["2026-05-01", "洗车"],
    },
    {
        "content": "2026年5月15日玻璃水用完，加满。",
        "kind": "episodic",
        "cues": ["2026-05-15", "玻璃水"],
    },
    {
        "content": "2026年6月1日预约 6 月 10 日四轮定位。",
        "kind": "episodic",
        "cues": ["2026-06-01", "四轮定位"],
    },
    {
        "content": "2026年6月10日四轮定位完成。",
        "kind": "episodic",
        "cues": ["2026-06-10", "四轮定位"],
    },
    {
        "content": "2026年6月20日电瓶检测：健康度 85%。",
        "kind": "episodic",
        "cues": ["2026-06-20", "电瓶"],
    },
    {
        "content": "2026年7月1日违章处理：违停 200 元，6 月 28 日。",
        "kind": "episodic",
        "cues": ["2026-07-01", "违章"],
    },
    {
        "content": "2026年7月10日预约 7 月 20 日年检。",
        "kind": "episodic",
        "cues": ["2026-07-10", "年检"],
    },
    {
        "content": "2026年7月20日年检通过。",
        "kind": "episodic",
        "cues": ["2026-07-20", "年检"],
    },
    {
        "content": "2026年7月25日空调不制冷，7 月 28 日修好。",
        "kind": "episodic",
        "cues": ["2026-07-25", "空调"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日三保。",
        "kind": "episodic",
        "cues": ["2026-08-01", "三保"],
    },
    {
        "content": "2026年8月5日轮胎气压告警，8 月 6 日打气。",
        "kind": "episodic",
        "cues": ["2026-08-05", "轮胎"],
    },
    {
        "content": "保养手册：每 5000km 或半年保养。",
        "kind": "semantic",
        "cues": ["保养手册"],
    },
    {
        "content": "加油优惠：中石化每周三 95 折。",
        "kind": "semantic",
        "cues": ["加油优惠"],
    },
    {
        "content": "停车位：小区地下 B2-118，月租 400 元。",
        "kind": "semantic",
        "cues": ["停车位", "B2"],
    },
    {
        "content": "保险客服 95510。",
        "kind": "semantic",
        "cues": ["保险", "电话"],
    },
    {
        "content": "车钥匙备用放家里抽屉。",
        "kind": "semantic",
        "cues": ["钥匙"],
    },
]


QUESTIONS = [
    {
        "dim": "车辆信息",
        "q": "车是什么型号？落地多少钱？",
        "answer": "比亚迪海豹，18.6万",
        "terms": ["海豹"],
    },
    {
        "dim": "保养记录",
        "q": "上次保养是什么时候？里程多少？",
        "answer": "4月20日，8300km",
        "terms": ["8300"],
    },
    {
        "dim": "未来安排",
        "q": "下次保养是什么时候？",
        "answer": "8月12日三保",
        "terms": ["12"],
    },
    {
        "dim": "维修记录",
        "q": "上次修车是什么时候？修的什么？",
        "answer": "7月28日，空调",
        "terms": ["空调"],
    },
    {
        "dim": "保险信息",
        "q": "保险一年多少钱？客服电话多少？",
        "answer": "5200元，95510",
        "terms": ["5200", "95510"],
    },
    {
        "dim": "违章记录",
        "q": "上次违章是什么？罚多少？",
        "answer": "违停，200元",
        "terms": ["违停", "200"],
    },
    {
        "dim": "轮胎记录",
        "q": "上次轮胎出问题是什么时候？",
        "answer": "8月5日轮胎气压告警",
        "terms": ["告警"],
    },
    {
        "dim": "年检记录",
        "q": "年检通过了吗？什么时候？",
        "answer": "7月20日通过",
        "terms": ["20"],
    },
    {
        "dim": "停车位",
        "q": "车位在哪？月租多少？",
        "answer": "B2-118，400元",
        "terms": ["B2"],
    },
    {
        "dim": "保养规则",
        "q": "多久保养一次？",
        "answer": "5000km或半年",
        "terms": ["5000"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="汽车保养",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="car_mem0db",
        out_name="car_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
