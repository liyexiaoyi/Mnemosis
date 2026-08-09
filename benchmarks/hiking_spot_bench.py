"""Weekend-outdoors spot-check (round 320): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日买登山鞋。",
        "kind": "episodic",
        "cues": ["2026-01-10", "登山鞋"],
    },
    {
        "content": "2026年1月20日第一次徒步。",
        "kind": "episodic",
        "cues": ["2026-01-20", "徒步"],
    },
    {
        "content": "2026年2月1日预约 2 月 15 日爬山。",
        "kind": "episodic",
        "cues": ["2026-02-01", "爬山"],
    },
    {
        "content": "2026年2月15日爬山完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "爬山"],
    },
    {
        "content": "2026年3月1日买登山杖。",
        "kind": "episodic",
        "cues": ["2026-03-01", "登山杖"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日露营。",
        "kind": "episodic",
        "cues": ["2026-03-15", "露营"],
    },
    {
        "content": "2026年3月25日露营完成。",
        "kind": "episodic",
        "cues": ["2026-03-25", "露营"],
    },
    {
        "content": "2026年4月1日买帐篷。",
        "kind": "episodic",
        "cues": ["2026-04-01", "帐篷"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日骑行。",
        "kind": "episodic",
        "cues": ["2026-04-15", "骑行"],
    },
    {
        "content": "2026年4月25日骑行完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "骑行"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日溯溪。",
        "kind": "episodic",
        "cues": ["2026-05-01", "溯溪"],
    },
    {
        "content": "2026年5月15日溯溪完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "溯溪"],
    },
    {
        "content": "2026年6月1日买防晒霜。",
        "kind": "episodic",
        "cues": ["2026-06-01", "防晒霜"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日夜爬。",
        "kind": "episodic",
        "cues": ["2026-06-15", "夜爬"],
    },
    {
        "content": "2026年6月25日夜爬完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "夜爬"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日漂流。",
        "kind": "episodic",
        "cues": ["2026-07-01", "漂流"],
    },
    {
        "content": "2026年7月15日漂流完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "漂流"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日徒步。",
        "kind": "episodic",
        "cues": ["2026-08-01", "徒步"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日补防晒。",
        "kind": "episodic",
        "cues": ["2026-08-05", "防晒"],
    },
    {
        "content": "户外店电话 400-888-5555。",
        "kind": "semantic",
        "cues": ["户外店", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "户外装备",
        "q": "买了什么装备？",
        "answer": "防晒霜",
        "terms": ["防晒霜"],
    },
    {
        "dim": "爬山记录",
        "q": "上次爬山是什么时候？",
        "answer": "2月15日",
        "terms": ["15"],
    },
    {
        "dim": "露营",
        "q": "露营什么时候？",
        "answer": "3月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次徒步是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "骑行",
        "q": "骑行什么时候？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "溯溪",
        "q": "溯溪什么时候？",
        "answer": "5月15日",
        "terms": ["15"],
    },
    {
        "dim": "夜爬",
        "q": "夜爬什么时候？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "漂流",
        "q": "漂流什么时候？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "户外店",
        "q": "户外店电话多少？",
        "answer": "400-888-5555",
        "terms": ["5555"],
    },
    {
        "dim": "防晒提醒",
        "q": "什么时候补防晒？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="周末户外",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="hiking_mem0db",
        out_name="hiking_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
