"""Home-storage spot-check (round 312): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日买收纳箱。",
        "kind": "episodic",
        "cues": ["2026-01-10", "收纳箱"],
    },
    {
        "content": "2026年1月20日换季衣物收纳。",
        "kind": "episodic",
        "cues": ["2026-01-20", "换季"],
    },
    {
        "content": "2026年2月1日预约 2 月 10 日整理师。",
        "kind": "episodic",
        "cues": ["2026-02-01", "整理师"],
    },
    {
        "content": "2026年2月10日整理完成。",
        "kind": "episodic",
        "cues": ["2026-02-10", "整理师"],
    },
    {
        "content": "2026年3月1日买真空压缩袋。",
        "kind": "episodic",
        "cues": ["2026-03-01", "压缩袋"],
    },
    {
        "content": "2026年3月15日被子用真空压缩袋压缩。",
        "kind": "episodic",
        "cues": ["2026-03-15", "被子"],
    },
    {
        "content": "2026年4月1日储物间整理。",
        "kind": "episodic",
        "cues": ["2026-04-01", "储物间"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日扔旧物。",
        "kind": "episodic",
        "cues": ["2026-04-15", "旧物"],
    },
    {
        "content": "2026年4月25日旧物回收。",
        "kind": "episodic",
        "cues": ["2026-04-25", "旧物"],
    },
    {
        "content": "2026年5月1日买置物架。",
        "kind": "episodic",
        "cues": ["2026-05-01", "置物架"],
    },
    {
        "content": "2026年5月20日预约 6 月 1 日防潮。",
        "kind": "episodic",
        "cues": ["2026-05-20", "防潮"],
    },
    {
        "content": "2026年6月1日防潮完成。",
        "kind": "episodic",
        "cues": ["2026-06-01", "防潮"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日换季收纳。",
        "kind": "episodic",
        "cues": ["2026-07-01", "换季"],
    },
    {
        "content": "2026年7月15日收纳完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "换季"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日买新收纳箱。",
        "kind": "episodic",
        "cues": ["2026-08-01", "收纳箱"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日防潮包更换。",
        "kind": "episodic",
        "cues": ["2026-08-05", "防潮包"],
    },
    {
        "content": "收纳位置：客厅柜、卧室床底。",
        "kind": "semantic",
        "cues": ["收纳位置"],
    },
    {
        "content": "收纳标签：按季节。",
        "kind": "semantic",
        "cues": ["标签"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日社区跳蚤市场。",
        "kind": "episodic",
        "cues": ["2026-08-08", "跳蚤市场"],
    },
]


QUESTIONS = [
    {
        "dim": "收纳位置",
        "q": "东西收在哪？",
        "answer": "客厅柜、卧室床底",
        "terms": ["床底"],
    },
    {
        "dim": "整理师",
        "q": "整理师什么时候来的？",
        "answer": "2月10日",
        "terms": ["10"],
    },
    {
        "dim": "旧物回收",
        "q": "旧物什么时候回收的？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次买收纳箱是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "防潮",
        "q": "防潮什么时候做的？",
        "answer": "6月1日",
        "terms": ["1"],
    },
    {
        "dim": "换季收纳",
        "q": "上次换季收纳是什么时候？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "收纳标签",
        "q": "收纳怎么贴标签？",
        "answer": "按季节",
        "terms": ["季节"],
    },
    {
        "dim": "被子收纳",
        "q": "被子用什么压缩？",
        "answer": "真空压缩袋",
        "terms": ["压缩袋"],
    },
    {
        "dim": "跳蚤市场",
        "q": "跳蚤市场什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "防潮包",
        "q": "防潮包什么时候更换？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭收纳",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="storage_mem0db",
        out_name="storage_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
