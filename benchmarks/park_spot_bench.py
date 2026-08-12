"""Family-park spot-check (round 298): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日办公园年卡：家庭卡 600 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "年卡"],
    },
    {
        "content": "2026年1月20日第一次去公园。",
        "kind": "episodic",
        "cues": ["2026-01-20", "公园"],
    },
    {
        "content": "2026年2月1日预约 2 月 15 日动物园。",
        "kind": "episodic",
        "cues": ["2026-02-01", "动物园"],
    },
    {
        "content": "2026年2月15日动物园一日游。",
        "kind": "episodic",
        "cues": ["2026-02-15", "动物园"],
    },
    {
        "content": "2026年3月1日公园花展：3 月 20 日开幕。",
        "kind": "episodic",
        "cues": ["2026-03-01", "花展"],
    },
    {
        "content": "2026年3月20日花展开幕。",
        "kind": "episodic",
        "cues": ["2026-03-20", "花展"],
    },
    {
        "content": "2026年4月1日预约 4 月 15 日野餐。",
        "kind": "episodic",
        "cues": ["2026-04-01", "野餐"],
    },
    {
        "content": "2026年4月15日野餐完成。",
        "kind": "episodic",
        "cues": ["2026-04-15", "野餐"],
    },
    {
        "content": "2026年5月1日游乐园新项目：过山车。",
        "kind": "semantic",
        "cues": ["游乐园", "过山车"],
    },
    {
        "content": "2026年5月20日预约 5 月 30 日游乐园。",
        "kind": "episodic",
        "cues": ["2026-05-20", "游乐园"],
    },
    {
        "content": "2026年5月30日游乐园一日。",
        "kind": "episodic",
        "cues": ["2026-05-30", "游乐园"],
    },
    {
        "content": "2026年6月1日公园夜场：6 月 15 日开放。",
        "kind": "episodic",
        "cues": ["2026-06-01", "夜场"],
    },
    {
        "content": "2026年6月15日夜场开放。",
        "kind": "episodic",
        "cues": ["2026-06-15", "夜场"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日水上乐园。",
        "kind": "episodic",
        "cues": ["2026-07-01", "水上乐园"],
    },
    {
        "content": "2026年7月10日水上乐园。",
        "kind": "episodic",
        "cues": ["2026-07-10", "水上乐园"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日动物园夜游。",
        "kind": "episodic",
        "cues": ["2026-08-01", "夜游"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日年卡续费。",
        "kind": "episodic",
        "cues": ["2026-08-05", "续费"],
    },
    {
        "content": "公园客服 400-777-5555。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "公园开放：6:00-22:00。",
        "kind": "semantic",
        "cues": ["开放时间"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日音乐节。",
        "kind": "episodic",
        "cues": ["2026-08-08", "音乐节"],
    },
]


QUESTIONS = [
    {
        "dim": "年卡费用",
        "q": "公园年卡多少钱？",
        "answer": "600元",
        "terms": ["600"],
    },
    {
        "dim": "动物园记录",
        "q": "上次去动物园是什么时候？",
        "answer": "2月15日",
        "terms": ["15"],
    },
    {
        "dim": "未来安排",
        "q": "下次动物园夜游是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "花展记录",
        "q": "花展什么时候开幕？",
        "answer": "3月20日",
        "terms": ["20"],
    },
    {
        "dim": "野餐记录",
        "q": "上次野餐是什么时候？",
        "answer": "4月15日",
        "terms": ["15"],
    },
    {
        "dim": "新项目",
        "q": "游乐园新项目是什么？",
        "answer": "过山车",
        "terms": ["过山车"],
    },
    {
        "dim": "夜场开放",
        "q": "公园夜场什么时候开放？",
        "answer": "6月15日",
        "terms": ["15"],
    },
    {
        "dim": "客服电话",
        "q": "公园客服电话多少？",
        "answer": "400-777-5555",
        "terms": ["5555"],
    },
    {
        "dim": "开放时间",
        "q": "公园几点开放？",
        "answer": "6:00-22:00",
        "terms": ["6"],
    },
    {
        "dim": "音乐节",
        "q": "音乐节什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="公园年卡",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="park_mem0db",
        out_name="park_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
