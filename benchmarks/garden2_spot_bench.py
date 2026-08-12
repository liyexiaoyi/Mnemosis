"""Community-garden spot-check (round 338): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月11日认领社区花园1号菜地，年费150元。",
        "kind": "episodic",
        "cues": ["2026-01-11", "菜地"],
    },
    {
        "content": "2026年1月18日第一次去菜地种菜。",
        "kind": "episodic",
        "cues": ["2026-01-18", "种菜"],
    },
    {
        "content": "花园开放时间：每天早7点到晚7点。",
        "kind": "semantic",
        "cues": ["开放时间", "7点"],
    },
    {
        "content": "管理员电话 0571-3333-2222。",
        "kind": "semantic",
        "cues": ["管理员", "电话"],
    },
    {
        "content": "种植规则：每块菜地最多种3种作物。",
        "kind": "semantic",
        "cues": ["种植", "规则"],
    },
    {
        "content": "2026年2月15日购买番茄苗和黄瓜种子。",
        "kind": "episodic",
        "cues": ["2026-02-15", "种子"],
    },
    {
        "content": "2026年3月2日收到通知：3月16日花园浇水日。",
        "kind": "episodic",
        "cues": ["2026-03-02", "浇水"],
    },
    {
        "content": "2026年3月16日浇水日完成。",
        "kind": "episodic",
        "cues": ["2026-03-16", "浇水"],
    },
    {
        "content": "2026年4月6日预约4月20日工具借用：锄头和喷壶。",
        "kind": "episodic",
        "cues": ["2026-04-06", "工具"],
    },
    {
        "content": "2026年4月20日借用工具完成。",
        "kind": "episodic",
        "cues": ["2026-04-20", "工具"],
    },
    {
        "content": "2026年5月10日收到通知：5月28日社区花园评比。",
        "kind": "episodic",
        "cues": ["2026-05-10", "评比"],
    },
    {
        "content": "2026年5月28日评比完成，1号菜地获最佳整洁奖。",
        "kind": "episodic",
        "cues": ["2026-05-28", "评比"],
    },
    {
        "content": "2026年6月5日采摘第一批番茄。",
        "kind": "episodic",
        "cues": ["2026-06-05", "采摘"],
    },
    {
        "content": "2026年6月20日收到通知：7月6日花园有机肥领取。",
        "kind": "episodic",
        "cues": ["2026-06-20", "有机肥"],
    },
    {
        "content": "2026年7月6日领取有机肥两袋。",
        "kind": "episodic",
        "cues": ["2026-07-06", "有机肥"],
    },
    {
        "content": "2026年7月15日预约7月28日黄瓜采摘。",
        "kind": "episodic",
        "cues": ["2026-07-15", "黄瓜"],
    },
    {
        "content": "2026年7月28日黄瓜采摘完成。",
        "kind": "episodic",
        "cues": ["2026-07-28", "黄瓜"],
    },
    {
        "content": "2026年8月5日收到通知：8月19日秋季菜地整理活动。",
        "kind": "episodic",
        "cues": ["2026-08-05", "整理"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日年费续缴。",
        "kind": "episodic",
        "cues": ["2026-08-10", "续缴"],
    },
    {
        "content": "2026年8月12日收到通知：8月30日社区园艺讲座。",
        "kind": "episodic",
        "cues": ["2026-08-12", "讲座"],
    },
]


QUESTIONS = [
    {
        "dim": "认领菜地",
        "q": "菜地第一次是什么时候认领的？",
        "answer": "1月11日",
        "terms": ["11"],
    },
    {
        "dim": "年费",
        "q": "认领菜地一年多少钱？",
        "answer": "150元",
        "terms": ["150"],
    },
    {
        "dim": "下次活动",
        "q": "下次花园活动是什么时候？",
        "answer": "8月19日",
        "terms": ["19"],
    },
    {
        "dim": "开放时间",
        "q": "花园几点开门？",
        "answer": "早7点",
        "terms": ["7"],
    },
    {
        "dim": "管理员电话",
        "q": "花园管理员电话多少？",
        "answer": "0571-3333-2222",
        "terms": ["2222"],
    },
    {
        "dim": "种植规则",
        "q": "一块菜地最多种几种作物？",
        "answer": "3种",
        "terms": ["3"],
    },
    {
        "dim": "番茄采摘",
        "q": "第一批番茄什么时候采摘的？",
        "answer": "6月5日",
        "terms": ["5"],
    },
    {
        "dim": "评比",
        "q": "花园评比什么时候？",
        "answer": "5月28日",
        "terms": ["28"],
    },
    {
        "dim": "年费续缴",
        "q": "菜地年费什么时候续缴？",
        "answer": "8月25日",
        "terms": ["25"],
    },
    {
        "dim": "园艺讲座",
        "q": "园艺讲座什么时候？",
        "answer": "8月30日",
        "terms": ["30"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="社区花园",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="garden2_mem0db",
        out_name="garden2_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
