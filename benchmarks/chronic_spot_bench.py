"""Chronic-condition management spot-check (round 280): Mnemosis vs mem0."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日确诊高血压，医生开氨氯地平。",
        "kind": "episodic",
        "cues": ["2026-01-10", "高血压"],
    },
    {
        "content": "2026年1月15日买血压计：欧姆龙 299 元。",
        "kind": "episodic",
        "cues": ["2026-01-15", "血压计"],
    },
    {
        "content": "2026年1月20日血压记录：145/95。",
        "kind": "episodic",
        "cues": ["2026-01-20", "血压"],
    },
    {
        "content": "2026年2月1日开始每日服药。",
        "kind": "episodic",
        "cues": ["2026-02-01", "服药"],
    },
    {
        "content": "2026年2月15日复查：血压 138/88，医生调整剂量。",
        "kind": "episodic",
        "cues": ["2026-02-15", "复查"],
    },
    {
        "content": "2026年3月1日血糖偏高，加测空腹血糖。",
        "kind": "episodic",
        "cues": ["2026-03-01", "血糖"],
    },
    {
        "content": "2026年3月10日空腹血糖 6.8。",
        "kind": "episodic",
        "cues": ["2026-03-10", "血糖"],
    },
    {
        "content": "2026年4月1日预约 4 月 15 日复查。",
        "kind": "episodic",
        "cues": ["2026-04-01", "复查"],
    },
    {
        "content": "2026年4月15日复查：血压 132/85，血糖 6.2。",
        "kind": "episodic",
        "cues": ["2026-04-15", "复查"],
    },
    {
        "content": "2026年5月1日开始低盐饮食。",
        "kind": "episodic",
        "cues": ["2026-05-01", "低盐"],
    },
    {
        "content": "2026年5月20日血压计校准。",
        "kind": "episodic",
        "cues": ["2026-05-20", "校准"],
    },
    {
        "content": "2026年6月1日预约 6 月 15 日糖化血红蛋白检查。",
        "kind": "episodic",
        "cues": ["2026-06-01", "糖化"],
    },
    {
        "content": "2026年6月15日糖化血红蛋白 6.4%。",
        "kind": "episodic",
        "cues": ["2026-06-15", "糖化"],
    },
    {
        "content": "2026年7月1日换药：缬沙坦。",
        "kind": "episodic",
        "cues": ["2026-07-01", "换药"],
    },
    {
        "content": "2026年7月10日血压记录：128/82。",
        "kind": "episodic",
        "cues": ["2026-07-10", "血压"],
    },
    {
        "content": "2026年7月25日预约 8 月 5 日眼科检查。",
        "kind": "episodic",
        "cues": ["2026-07-25", "眼科"],
    },
    {
        "content": "2026年8月5日眼科检查：眼底正常。",
        "kind": "episodic",
        "cues": ["2026-08-05", "眼科"],
    },
    {
        "content": "2026年8月8日收到提醒：8 月 15 日药快吃完。",
        "kind": "episodic",
        "cues": ["2026-08-08", "药"],
    },
    {
        "content": "用药：氨氯地平 5mg 每天一次。",
        "kind": "semantic",
        "cues": ["用药", "氨氯地平"],
    },
    {
        "content": "饮食：每天盐 <5g。",
        "kind": "semantic",
        "cues": ["饮食", "盐"],
    },
    {
        "content": "运动：每天快走 30 分钟。",
        "kind": "semantic",
        "cues": ["运动"],
    },
    {
        "content": "医保报销：慢病门诊报销 70%。",
        "kind": "semantic",
        "cues": ["医保", "报销"],
    },
    {
        "content": "医生电话 139-5555-6666。",
        "kind": "semantic",
        "cues": ["医生", "电话"],
    },
    {
        "content": "2026年8月9日预约 8 月 20 日复查。",
        "kind": "episodic",
        "cues": ["2026-08-09", "复查"],
    },
]


QUESTIONS = [
    {
        "dim": "确诊记录",
        "q": "什么时候确诊高血压？",
        "answer": "1月10日",
        "terms": ["10"],
    },
    {
        "dim": "血压记录",
        "q": "上次血压多少？",
        "answer": "128/82",
        "terms": ["128"],
    },
    {
        "dim": "当前用药",
        "q": "现在吃什么药？",
        "answer": "缬沙坦",
        "terms": ["缬沙坦"],
    },
    {
        "dim": "血糖指标",
        "q": "糖化血红蛋白多少？",
        "answer": "6.4%",
        "terms": ["6.4"],
    },
    {
        "dim": "未来安排",
        "q": "下次复查是什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
    {
        "dim": "检查记录",
        "q": "上次眼科检查是什么时候？结果如何？",
        "answer": "8月5日，眼底正常",
        "terms": ["眼底"],
    },
    {
        "dim": "饮食要求",
        "q": "每天盐摄入多少？",
        "answer": "小于5g",
        "terms": ["5"],
    },
    {
        "dim": "运动要求",
        "q": "每天运动多久？",
        "answer": "30分钟快走",
        "terms": ["30"],
    },
    {
        "dim": "医保报销",
        "q": "慢病门诊报销多少？",
        "answer": "70%",
        "terms": ["70"],
    },
    {
        "dim": "用药提醒",
        "q": "药什么时候快吃完？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="慢病管理",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="chronic_mem0db",
        out_name="chronic_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
