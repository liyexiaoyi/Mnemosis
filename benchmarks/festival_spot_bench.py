"""Festival-shopping spot-check (round 305): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日春节采购清单。",
        "kind": "semantic",
        "cues": ["春节", "清单"],
    },
    {
        "content": "2026年1月20日买年货：坚果 300 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "年货"],
    },
    {
        "content": "2026年2月1日除夕年夜饭：家宴 800 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "年夜饭"],
    },
    {
        "content": "2026年2月15日元宵节买汤圆。",
        "kind": "episodic",
        "cues": ["2026-02-15", "元宵"],
    },
    {
        "content": "2026年3月1日清明祭扫安排：3 月 30 日。",
        "kind": "episodic",
        "cues": ["2026-03-01", "清明"],
    },
    {
        "content": "2026年3月30日祭扫完成。",
        "kind": "episodic",
        "cues": ["2026-03-30", "清明"],
    },
    {
        "content": "2026年4月1日五一出行计划：4 月 30 日出发。",
        "kind": "episodic",
        "cues": ["2026-04-01", "五一"],
    },
    {
        "content": "2026年4月30日出发去杭州。",
        "kind": "episodic",
        "cues": ["2026-04-30", "杭州"],
    },
    {
        "content": "2026年5月5日回程。",
        "kind": "episodic",
        "cues": ["2026-05-05", "回程"],
    },
    {
        "content": "2026年6月1日端午买粽子。",
        "kind": "episodic",
        "cues": ["2026-06-01", "端午"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日包粽子活动。",
        "kind": "episodic",
        "cues": ["2026-06-15", "包粽子"],
    },
    {
        "content": "2026年6月25日包粽子完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "包粽子"],
    },
    {
        "content": "2026年7月1日暑期亲子游：7 月 20 日。",
        "kind": "episodic",
        "cues": ["2026-07-01", "亲子游"],
    },
    {
        "content": "2026年7月20日出发亲子游。",
        "kind": "episodic",
        "cues": ["2026-07-20", "亲子游"],
    },
    {
        "content": "2026年8月1日中秋采购：8 月 30 日。",
        "kind": "episodic",
        "cues": ["2026-08-01", "中秋"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日订月饼。",
        "kind": "episodic",
        "cues": ["2026-08-05", "月饼"],
    },
    {
        "content": "年货清单：春联、坚果、糖果。",
        "kind": "semantic",
        "cues": ["年货", "清单"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日社区中秋活动。",
        "kind": "episodic",
        "cues": ["2026-08-08", "中秋活动"],
    },
]


QUESTIONS = [
    {
        "dim": "年货清单",
        "q": "年货买了什么？",
        "answer": "坚果",
        "terms": ["坚果"],
    },
    {
        "dim": "年夜饭",
        "q": "年夜饭多少钱？",
        "answer": "800元",
        "terms": ["800"],
    },
    {
        "dim": "清明祭扫",
        "q": "清明祭扫什么时候？",
        "answer": "3月30日",
        "terms": ["30"],
    },
    {
        "dim": "五一出行",
        "q": "五一去哪？",
        "answer": "杭州",
        "terms": ["杭州"],
    },
    {
        "dim": "月饼提醒",
        "q": "什么时候订月饼？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "包粽子",
        "q": "包粽子活动什么时候？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "亲子游",
        "q": "暑期亲子游什么时候出发？",
        "answer": "7月20日",
        "terms": ["20"],
    },
    {
        "dim": "元宵采购",
        "q": "元宵节买了什么？",
        "answer": "汤圆",
        "terms": ["汤圆"],
    },
    {
        "dim": "中秋采购",
        "q": "中秋采购什么时候？",
        "answer": "8月30日",
        "terms": ["30"],
    },
    {
        "dim": "社区活动",
        "q": "社区中秋活动什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭节日",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="festival_mem0db",
        out_name="festival_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
