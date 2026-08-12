"""Pet-training-school spot-check (round 332): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月8日给狗狗报名宠物训练学校，基础班3000元。",
        "kind": "episodic",
        "cues": ["2026-01-08", "报名"],
    },
    {
        "content": "2026年1月15日第一次送狗狗去训练。",
        "kind": "episodic",
        "cues": ["2026-01-15", "训练"],
    },
    {
        "content": "训练学校每周日上午上课，每次1小时。",
        "kind": "semantic",
        "cues": ["课表", "周日"],
    },
    {
        "content": "2026年2月10日训练项目：坐下、趴下、随行、拒食。",
        "kind": "episodic",
        "cues": ["2026-02-10", "项目"],
    },
    {
        "content": "2026年2月25日购买训练零食和牵引绳。",
        "kind": "episodic",
        "cues": ["2026-02-25", "购买"],
    },
    {
        "content": "2026年3月5日收到通知：3月20日基础班结业考试。",
        "kind": "episodic",
        "cues": ["2026-03-05", "结业"],
    },
    {
        "content": "2026年3月20日结业考试通过，狗狗获得优秀学员奖。",
        "kind": "episodic",
        "cues": ["2026-03-20", "结业"],
    },
    {
        "content": "训练学校教练电话 135-1111-2222。",
        "kind": "semantic",
        "cues": ["教练", "电话"],
    },
    {
        "content": "请假规则：提前两天联系教练调课。",
        "kind": "semantic",
        "cues": ["请假", "调课"],
    },
    {
        "content": "2026年4月6日预约4月25日狗狗才艺展示会。",
        "kind": "episodic",
        "cues": ["2026-04-06", "展示会"],
    },
    {
        "content": "2026年4月25日才艺展示会完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "展示会"],
    },
    {
        "content": "2026年5月11日狗狗接种狂犬疫苗。",
        "kind": "episodic",
        "cues": ["2026-05-11", "疫苗"],
    },
    {
        "content": "2026年5月20日预约5月30日训练学校健康检查。",
        "kind": "episodic",
        "cues": ["2026-05-20", "健康检查"],
    },
    {
        "content": "2026年5月30日健康检查通过。",
        "kind": "episodic",
        "cues": ["2026-05-30", "健康检查"],
    },
    {
        "content": "2026年6月8日报名进阶班，费用5000元。",
        "kind": "episodic",
        "cues": ["2026-06-08", "进阶班"],
    },
    {
        "content": "2026年7月2日收到通知：7月20日宠物运动会。",
        "kind": "episodic",
        "cues": ["2026-07-02", "运动会"],
    },
    {
        "content": "2026年7月20日宠物运动会完成，狗狗获得跑步第二名。",
        "kind": "episodic",
        "cues": ["2026-07-20", "运动会"],
    },
    {
        "content": "2026年8月3日预约8月16日进阶班复课。",
        "kind": "episodic",
        "cues": ["2026-08-03", "复课"],
    },
    {
        "content": "2026年8月10日收到提醒：8月28日狗狗训导公开课。",
        "kind": "episodic",
        "cues": ["2026-08-10", "公开课"],
    },
    {
        "content": "接送安排：训练学校提供上门接送，需提前一天预约。",
        "kind": "semantic",
        "cues": ["接送", "预约"],
    },
]


QUESTIONS = [
    {
        "dim": "报名时间",
        "q": "狗狗训练班第一次报名是什么时候？",
        "answer": "1月8日",
        "terms": ["8"],
    },
    {
        "dim": "基础班费用",
        "q": "基础班多少钱？",
        "answer": "3000元",
        "terms": ["3000"],
    },
    {
        "dim": "下次复课",
        "q": "下次训练课是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "上课时间",
        "q": "训练课每周几上？",
        "answer": "周日",
        "terms": ["周日"],
    },
    {
        "dim": "训练项目",
        "q": "狗狗学了哪些训练项目？",
        "answer": "坐下、趴下、随行、拒食",
        "terms": ["拒食"],
    },
    {
        "dim": "教练电话",
        "q": "训练学校教练电话多少？",
        "answer": "135-1111-2222",
        "terms": ["2222"],
    },
    {
        "dim": "请假调课",
        "q": "训练课请假怎么处理？",
        "answer": "提前两天联系教练调课",
        "terms": ["两天"],
    },
    {
        "dim": "公开课",
        "q": "训导公开课什么时候？",
        "answer": "8月28日",
        "terms": ["28"],
    },
    {
        "dim": "疫苗记录",
        "q": "狗狗什么时候打的狂犬疫苗？",
        "answer": "5月11日",
        "terms": ["11"],
    },
    {
        "dim": "接送安排",
        "q": "训练学校接送怎么安排？",
        "answer": "上门接送，提前一天预约",
        "terms": ["上门"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="宠物训练学校",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="pet_training_mem0db",
        out_name="pet_training_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
