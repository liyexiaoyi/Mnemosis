"""Old-book-recycling spot-check (round 341): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月6日第一次预约旧书回收，上门回收20本书。",
        "kind": "episodic",
        "cues": ["2026-01-06", "回收"],
    },
    {
        "content": "2026年1月10日回收完成，获得35元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "回收"],
    },
    {
        "content": "回收站营业时间：早8点到晚6点。",
        "kind": "semantic",
        "cues": ["营业时间", "8点"],
    },
    {
        "content": "回收站电话 0451-6666-3333。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "回收范围：教材、小说、杂志均可，不收字典。",
        "kind": "semantic",
        "cues": ["范围", "教材"],
    },
    {
        "content": "2026年2月8日预约2月20日第二次回收。",
        "kind": "episodic",
        "cues": ["2026-02-08", "回收"],
    },
    {
        "content": "2026年2月20日回收15本书，获得28元。",
        "kind": "episodic",
        "cues": ["2026-02-20", "回收"],
    },
    {
        "content": "积分规则：每回收1本积1分。",
        "kind": "semantic",
        "cues": ["积分", "规则"],
    },
    {
        "content": "2026年3月5日收到通知：3月18日书香捐赠活动。",
        "kind": "episodic",
        "cues": ["2026-03-05", "捐赠"],
    },
    {
        "content": "2026年3月18日捐赠20本书给山区小学。",
        "kind": "episodic",
        "cues": ["2026-03-18", "捐赠"],
    },
    {
        "content": "消毒说明：回收书籍统一消毒处理。",
        "kind": "semantic",
        "cues": ["消毒", "说明"],
    },
    {
        "content": "2026年4月12日预约4月25日上门回收。",
        "kind": "episodic",
        "cues": ["2026-04-12", "回收"],
    },
    {
        "content": "2026年4月25日回收10本书，获得18元。",
        "kind": "episodic",
        "cues": ["2026-04-25", "回收"],
    },
    {
        "content": "预约规则：上门回收需提前一天预约。",
        "kind": "semantic",
        "cues": ["预约", "规则"],
    },
    {
        "content": "2026年5月15日收到通知：5月30日旧书市集。",
        "kind": "episodic",
        "cues": ["2026-05-15", "市集"],
    },
    {
        "content": "2026年5月30日旧书市集完成。",
        "kind": "episodic",
        "cues": ["2026-05-30", "市集"],
    },
    {
        "content": "2026年6月20日预约7月2日上门回收。",
        "kind": "episodic",
        "cues": ["2026-06-20", "回收"],
    },
    {
        "content": "2026年7月2日回收12本书，获得22元。",
        "kind": "episodic",
        "cues": ["2026-07-02", "回收"],
    },
    {
        "content": "2026年8月4日预约8月17日上门回收。",
        "kind": "episodic",
        "cues": ["2026-08-04", "回收"],
    },
    {
        "content": "2026年8月10日收到提醒：8月22日积分兑换截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "积分"],
    },
]


QUESTIONS = [
    {
        "dim": "首次回收",
        "q": "第一次旧书回收是什么时候预约的？",
        "answer": "1月6日",
        "terms": ["6"],
    },
    {
        "dim": "回收金额",
        "q": "第一次回收获得多少钱？",
        "answer": "35元",
        "terms": ["35"],
    },
    {
        "dim": "下次上门",
        "q": "下次上门回收是什么时候？",
        "answer": "8月17日",
        "terms": ["17"],
    },
    {
        "dim": "营业时间",
        "q": "回收站几点开门？",
        "answer": "早8点",
        "terms": ["8"],
    },
    {
        "dim": "联系电话",
        "q": "回收站电话多少？",
        "answer": "0451-6666-3333",
        "terms": ["3333"],
    },
    {
        "dim": "回收范围",
        "q": "旧书回收收哪些书？",
        "answer": "教材、小说、杂志，不收字典",
        "terms": ["字典"],
    },
    {
        "dim": "积分规则",
        "q": "回收几本书积1分？",
        "answer": "1本",
        "terms": ["1"],
    },
    {
        "dim": "预约规则",
        "q": "上门回收要提前多久预约？",
        "answer": "提前一天",
        "terms": ["一天"],
    },
    {
        "dim": "消毒说明",
        "q": "回收的书籍怎么处理？",
        "answer": "统一消毒",
        "terms": ["消毒"],
    },
    {
        "dim": "积分兑换",
        "q": "积分兑换什么时候截止？",
        "answer": "8月22日",
        "terms": ["22"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="旧书回收",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="bookrecycle_mem0db",
        out_name="bookrecycle_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
