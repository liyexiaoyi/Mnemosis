"""Hospital-escort spot-check (round 323): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日预约 1 月 20 日陪诊。",
        "kind": "episodic",
        "cues": ["2026-01-10", "陪诊"],
    },
    {
        "content": "2026年1月20日陪爸妈看门诊。",
        "kind": "episodic",
        "cues": ["2026-01-20", "门诊"],
    },
    {
        "content": "2026年2月1日预约 2 月 15 日陪诊取药。",
        "kind": "episodic",
        "cues": ["2026-02-01", "取药"],
    },
    {
        "content": "2026年2月15日取药完成。",
        "kind": "episodic",
        "cues": ["2026-02-15", "取药"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日陪诊检查。",
        "kind": "episodic",
        "cues": ["2026-03-01", "检查"],
    },
    {
        "content": "2026年3月15日检查完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "检查"],
    },
    {
        "content": "2026年4月1日陪诊服务：300 元/天。",
        "kind": "semantic",
        "cues": ["陪诊", "300"],
    },
    {
        "content": "2026年4月15日预约 4 月 25 日陪诊复诊。",
        "kind": "episodic",
        "cues": ["2026-04-15", "复诊"],
    },
    {
        "content": "2026年4月25日复诊完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "复诊"],
    },
    {
        "content": "2026年5月1日买陪诊保险。",
        "kind": "episodic",
        "cues": ["2026-05-01", "保险"],
    },
    {
        "content": "2026年5月15日预约 5 月 25 日陪诊取报告。",
        "kind": "episodic",
        "cues": ["2026-05-15", "取报告"],
    },
    {
        "content": "2026年5月25日取报告完成。",
        "kind": "episodic",
        "cues": ["2026-05-25", "取报告"],
    },
    {
        "content": "2026年6月1日陪诊师小刘。",
        "kind": "semantic",
        "cues": ["陪诊师", "小刘"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日陪诊手术。",
        "kind": "episodic",
        "cues": ["2026-06-15", "手术"],
    },
    {
        "content": "2026年6月25日手术陪诊完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "手术"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日陪诊复查。",
        "kind": "episodic",
        "cues": ["2026-07-01", "复查"],
    },
    {
        "content": "2026年7月15日复查完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "复查"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日陪诊。",
        "kind": "episodic",
        "cues": ["2026-08-01", "陪诊"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日续陪诊套餐。",
        "kind": "episodic",
        "cues": ["2026-08-05", "套餐"],
    },
    {
        "content": "陪诊客服 400-888-1111。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
]


QUESTIONS = [
    {
        "dim": "陪诊价格",
        "q": "陪诊多少钱一天？",
        "answer": "300元",
        "terms": ["300"],
    },
    {
        "dim": "首次陪诊",
        "q": "第一次陪诊是什么时候？",
        "answer": "1月20日",
        "terms": ["20"],
    },
    {
        "dim": "复诊记录",
        "q": "上次陪诊复诊是什么时候？",
        "answer": "4月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次陪诊是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "陪诊师",
        "q": "陪诊师是谁？",
        "answer": "小刘",
        "terms": ["小刘"],
    },
    {
        "dim": "手术陪诊",
        "q": "手术陪诊什么时候？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "陪诊保险",
        "q": "买了什么？",
        "answer": "陪诊保险",
        "terms": ["陪诊保险"],
    },
    {
        "dim": "取报告",
        "q": "取报告什么时候？",
        "answer": "5月25日",
        "terms": ["25"],
    },
    {
        "dim": "陪诊客服",
        "q": "陪诊客服电话多少？",
        "answer": "400-888-1111",
        "terms": ["1111"],
    },
    {
        "dim": "续套餐",
        "q": "什么时候续陪诊套餐？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="医院陪诊",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="escort_mem0db",
        out_name="escort_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
