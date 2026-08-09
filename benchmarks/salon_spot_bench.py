"""Hair-salon spot-check (round 297): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日第一次去美发店。",
        "kind": "episodic",
        "cues": ["2026-01-10", "美发店"],
    },
    {
        "content": "2026年1月20日办卡：充 500 送 100。",
        "kind": "episodic",
        "cues": ["2026-01-20", "会员卡"],
    },
    {
        "content": "2026年2月1日剪发 58 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "剪发"],
    },
    {
        "content": "2026年2月15日染发：棕色，380 元。",
        "kind": "episodic",
        "cues": ["2026-02-15", "染发"],
    },
    {
        "content": "2026年3月1日烫发预约：3 月 15 日。",
        "kind": "episodic",
        "cues": ["2026-03-01", "烫发"],
    },
    {
        "content": "2026年3月15日烫发完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "烫发"],
    },
    {
        "content": "2026年4月1日预约 4 月 10 日护理。",
        "kind": "episodic",
        "cues": ["2026-04-01", "护理"],
    },
    {
        "content": "2026年4月10日护理完成。",
        "kind": "episodic",
        "cues": ["2026-04-10", "护理"],
    },
    {
        "content": "2026年5月1日理发师换人：新理发师 Tony。",
        "kind": "semantic",
        "cues": ["理发师", "Tony"],
    },
    {
        "content": "2026年5月20日预约 5 月 30 日剪发。",
        "kind": "episodic",
        "cues": ["2026-05-20", "剪发"],
    },
    {
        "content": "2026年5月30日剪发完成。",
        "kind": "episodic",
        "cues": ["2026-05-30", "剪发"],
    },
    {
        "content": "2026年6月1日染发褪色，6 月 10 日补色。",
        "kind": "episodic",
        "cues": ["2026-06-01", "褪色"],
    },
    {
        "content": "2026年6月10日补色完成。",
        "kind": "episodic",
        "cues": ["2026-06-10", "补色"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日剪发。",
        "kind": "episodic",
        "cues": ["2026-07-01", "剪发"],
    },
    {
        "content": "2026年7月10日剪发完成。",
        "kind": "episodic",
        "cues": ["2026-07-10", "剪发"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日烫发。",
        "kind": "episodic",
        "cues": ["2026-08-01", "烫发"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日会员卡到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "到期"],
    },
    {
        "content": "美发店电话 400-888-7777。",
        "kind": "semantic",
        "cues": ["美发店", "电话"],
    },
    {
        "content": "美发店地址：万达 2 楼。",
        "kind": "semantic",
        "cues": ["地址", "万达"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日会员日。",
        "kind": "episodic",
        "cues": ["2026-08-08", "会员日"],
    },
]


QUESTIONS = [
    {
        "dim": "会员卡",
        "q": "会员卡充多少送多少？",
        "answer": "充500送100",
        "terms": ["500", "100"],
    },
    {
        "dim": "染发记录",
        "q": "染发多少钱？什么颜色？",
        "answer": "380元，棕色",
        "terms": ["棕色"],
    },
    {
        "dim": "未来安排",
        "q": "下次烫发是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "理发师",
        "q": "现在理发师是谁？",
        "answer": "Tony",
        "terms": ["Tony"],
    },
    {
        "dim": "护理记录",
        "q": "上次护理是什么时候？",
        "answer": "4月10日",
        "terms": ["10"],
    },
    {
        "dim": "补色记录",
        "q": "染发褪色什么时候补的？",
        "answer": "6月10日",
        "terms": ["10"],
    },
    {
        "dim": "剪发价格",
        "q": "剪发多少钱？",
        "answer": "58元",
        "terms": ["58"],
    },
    {
        "dim": "美发店信息",
        "q": "美发店在哪？电话多少？",
        "answer": "万达2楼，400-888-7777",
        "terms": ["万达", "7777"],
    },
    {
        "dim": "到期提醒",
        "q": "会员卡什么时候到期？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "会员日",
        "q": "会员日什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="美发店会员",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="salon_mem0db",
        out_name="salon_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
