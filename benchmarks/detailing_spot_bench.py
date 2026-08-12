"""Car-detailing spot-check (round 322): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日预约 1 月 20 日镀晶。",
        "kind": "episodic",
        "cues": ["2026-01-10", "镀晶"],
    },
    {
        "content": "2026年1月20日镀晶完成。",
        "kind": "episodic",
        "cues": ["2026-01-20", "镀晶"],
    },
    {
        "content": "2026年2月1日洗车套餐：10 次卡。",
        "kind": "semantic",
        "cues": ["洗车卡", "10次"],
    },
    {
        "content": "2026年2月15日内饰清洁。",
        "kind": "episodic",
        "cues": ["2026-02-15", "内饰"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日打蜡。",
        "kind": "episodic",
        "cues": ["2026-03-01", "打蜡"],
    },
    {
        "content": "2026年3月15日打蜡完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "打蜡"],
    },
    {
        "content": "2026年4月1日补漆：4 月 10 日。",
        "kind": "episodic",
        "cues": ["2026-04-01", "补漆"],
    },
    {
        "content": "2026年4月10日补漆完成。",
        "kind": "episodic",
        "cues": ["2026-04-10", "补漆"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日玻璃镀膜。",
        "kind": "episodic",
        "cues": ["2026-05-01", "镀膜"],
    },
    {
        "content": "2026年5月15日镀膜完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "镀膜"],
    },
    {
        "content": "2026年6月1日轮胎养护。",
        "kind": "episodic",
        "cues": ["2026-06-01", "轮胎"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日除味。",
        "kind": "episodic",
        "cues": ["2026-06-15", "除味"],
    },
    {
        "content": "2026年6月25日除味完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "除味"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日座椅清洁。",
        "kind": "episodic",
        "cues": ["2026-07-01", "座椅"],
    },
    {
        "content": "2026年7月15日座椅清洁完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "座椅"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日抛光。",
        "kind": "episodic",
        "cues": ["2026-08-01", "抛光"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日洗车卡到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "洗车卡"],
    },
    {
        "content": "美容店电话 400-777-2222。",
        "kind": "semantic",
        "cues": ["美容店", "电话"],
    },
    {
        "content": "洗车卡余次：8 次。",
        "kind": "semantic",
        "cues": ["洗车卡", "余次"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日会员日。",
        "kind": "episodic",
        "cues": ["2026-08-08", "会员日"],
    },
]


QUESTIONS = [
    {
        "dim": "镀晶记录",
        "q": "镀晶什么时候做的？",
        "answer": "1月20日",
        "terms": ["20"],
    },
    {
        "dim": "洗车卡",
        "q": "洗车卡还有几次？",
        "answer": "8次",
        "terms": ["8"],
    },
    {
        "dim": "打蜡",
        "q": "打蜡什么时候？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "未来安排",
        "q": "下次抛光是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "补漆",
        "q": "补漆什么时候？",
        "answer": "4月10日",
        "terms": ["10"],
    },
    {
        "dim": "玻璃镀膜",
        "q": "玻璃镀膜什么时候？",
        "answer": "5月15日",
        "terms": ["15"],
    },
    {
        "dim": "除味",
        "q": "除味什么时候？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "座椅清洁",
        "q": "座椅清洁什么时候？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "美容店",
        "q": "美容店电话多少？",
        "answer": "400-777-2222",
        "terms": ["2222"],
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
        domain="汽车美容",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="detailing_mem0db",
        out_name="detailing_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
