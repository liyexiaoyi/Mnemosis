"""Fitness-training spot-check (round 267): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月5日办了健身卡：年卡 1880 元。",
        "kind": "episodic",
        "cues": ["2026-01-05", "健身卡"],
    },
    {
        "content": "2026年1月10日体测：体脂率 24%，体重 72kg。",
        "kind": "episodic",
        "cues": ["2026-01-10", "体测"],
    },
    {
        "content": "2026年1月12日请了私教：每周两节课，每节 260 元。",
        "kind": "semantic",
        "cues": ["私教", "260"],
    },
    {
        "content": "2026年1月15日第一节私教课：练胸，卧推空杆。",
        "kind": "episodic",
        "cues": ["2026-01-15", "私教"],
    },
    {
        "content": "2026年2月10日复查体测：体脂 23%。",
        "kind": "episodic",
        "cues": ["2026-02-10", "体测"],
    },
    {
        "content": "2026年2月20日私教课练腿：深蹲 40kg。",
        "kind": "episodic",
        "cues": ["2026-02-20", "私教"],
    },
    {
        "content": "2026年3月5日预约 3 月 15 日第二次体测。",
        "kind": "episodic",
        "cues": ["2026-03-05", "体测"],
    },
    {
        "content": "2026年3月15日体测：体脂 21%，体重 69kg。",
        "kind": "episodic",
        "cues": ["2026-03-15", "体测"],
    },
    {
        "content": "2026年3月20日私教课：卧推 50kg，5 组 × 8 次。",
        "kind": "episodic",
        "cues": ["2026-03-20", "卧推"],
    },
    {
        "content": "2026年4月2日买了蛋白粉：5 磅 329 元。",
        "kind": "episodic",
        "cues": ["2026-04-02", "蛋白粉"],
    },
    {
        "content": "2026年4月10日私教课练背：引体向上 6 个。",
        "kind": "episodic",
        "cues": ["2026-04-10", "练背"],
    },
    {
        "content": "2026年5月1日健身房通知：5 月 10 日器械维护。",
        "kind": "episodic",
        "cues": ["2026-05-01", "维护"],
    },
    {
        "content": "2026年5月10日器械维护完成，5 月 12 日恢复营业。",
        "kind": "episodic",
        "cues": ["2026-05-10", "维护"],
    },
    {
        "content": "2026年5月20日私教课：深蹲 70kg。",
        "kind": "episodic",
        "cues": ["2026-05-20", "深蹲"],
    },
    {
        "content": "2026年6月1日私教说 6 月 20 日有体能考核。",
        "kind": "episodic",
        "cues": ["2026-06-01", "考核"],
    },
    {
        "content": "2026年6月20日体能考核：3 分钟平板支撑。",
        "kind": "episodic",
        "cues": ["2026-06-20", "考核"],
    },
    {
        "content": "2026年7月2日买了运动手环：心率监测。",
        "kind": "episodic",
        "cues": ["2026-07-02", "手环"],
    },
    {
        "content": "2026年7月10日私教课：卧推 60kg。",
        "kind": "episodic",
        "cues": ["2026-07-10", "卧推"],
    },
    {
        "content": "2026年7月15日预约 7 月 28 日第三次体测。",
        "kind": "episodic",
        "cues": ["2026-07-15", "体测"],
    },
    {
        "content": "2026年7月20日教练提醒 8 月 1 日续费活动开始。",
        "kind": "episodic",
        "cues": ["2026-07-20", "续费"],
    },
    {
        "content": "2026年8月2日续费年卡：优惠价 1688 元。",
        "kind": "episodic",
        "cues": ["2026-08-02", "续费"],
    },
    {
        "content": "2026年8月5日私教课调时间：8 月 12 日改到 19:30。",
        "kind": "episodic",
        "cues": ["2026-08-05", "私教"],
    },
    {
        "content": "2026年8月8日约了 8 月 18 日的拉伸课。",
        "kind": "episodic",
        "cues": ["2026-08-08", "拉伸"],
    },
    {
        "content": "健身计划：每周 3 练：周一胸、周三背、周五腿。",
        "kind": "semantic",
        "cues": ["健身计划"],
    },
    {
        "content": "饮食记录：早餐 2 个蛋 + 燕麦，练后蛋白粉。",
        "kind": "semantic",
        "cues": ["饮食"],
    },
    {
        "content": "器材存放：私教课用 2 号锁柜，密码 2233。",
        "kind": "semantic",
        "cues": ["锁柜", "2233"],
    },
]


QUESTIONS = [
    {
        "dim": "体测记录",
        "q": "上次体测是什么时候？体脂率多少？",
        "answer": "3月15日，体脂21%",
        "terms": ["21"],
    },
    {
        "dim": "私教课程",
        "q": "上次私教课练了什么？",
        "answer": "卧推60kg",
        "terms": ["卧推", "60"],
    },
    {
        "dim": "未来安排",
        "q": "下次体测是什么时候？",
        "answer": "7月28日",
        "terms": ["28"],
    },
    {
        "dim": "续费记录",
        "q": "健身卡什么时候续的？多少钱？",
        "answer": "8月2日，1688元",
        "terms": ["1688"],
    },
    {
        "dim": "力量数据",
        "q": "现在卧推能推多少？",
        "answer": "60kg",
        "terms": ["60"],
    },
    {
        "dim": "训练计划",
        "q": "每周怎么练？",
        "answer": "周一胸、周三背、周五腿",
        "terms": ["背"],
    },
    {
        "dim": "饮食记录",
        "q": "练后吃什么？",
        "answer": "蛋白粉",
        "terms": ["蛋白粉"],
    },
    {
        "dim": "器械维护",
        "q": "上次器械维护是什么时候？",
        "answer": "5月10日",
        "terms": ["10"],
    },
    {
        "dim": "预约拉伸",
        "q": "下次拉伸课是什么时候？",
        "answer": "8月18日",
        "terms": ["18"],
    },
    {
        "dim": "器材存放",
        "q": "私教课用哪个柜子？密码多少？",
        "answer": "2号锁柜，密码2233",
        "terms": ["2233"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="健身训练",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="fitness_mem0db",
        out_name="fitness_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
