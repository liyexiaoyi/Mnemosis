"""Family-medicine spot-check (round 300): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日备家庭药箱。",
        "kind": "episodic",
        "cues": ["2026-01-10", "药箱"],
    },
    {
        "content": "2026年1月20日感冒药：布洛芬。",
        "kind": "semantic",
        "cues": ["感冒药", "布洛芬"],
    },
    {
        "content": "2026年2月1日药箱清单：创可贴、体温计。",
        "kind": "semantic",
        "cues": ["药箱", "创可贴"],
    },
    {
        "content": "2026年2月15日孩子发烧，用美林。",
        "kind": "episodic",
        "cues": ["2026-02-15", "美林"],
    },
    {
        "content": "2026年3月1日降压药：缬沙坦。",
        "kind": "semantic",
        "cues": ["降压药", "缬沙坦"],
    },
    {
        "content": "2026年3月15日预约 3 月 25 日换药。",
        "kind": "episodic",
        "cues": ["2026-03-15", "换药"],
    },
    {
        "content": "2026年3月25日换药完成。",
        "kind": "episodic",
        "cues": ["2026-03-25", "换药"],
    },
    {
        "content": "2026年4月1日过敏药：氯雷他定。",
        "kind": "semantic",
        "cues": ["过敏药", "氯雷他定"],
    },
    {
        "content": "2026年4月15日药箱补货。",
        "kind": "episodic",
        "cues": ["2026-04-15", "补货"],
    },
    {
        "content": "2026年5月1日眼药水：人工泪液。",
        "kind": "semantic",
        "cues": ["眼药水"],
    },
    {
        "content": "2026年5月20日预约 5 月 30 日药品回收。",
        "kind": "episodic",
        "cues": ["2026-05-20", "回收"],
    },
    {
        "content": "2026年5月30日回收过期药。",
        "kind": "episodic",
        "cues": ["2026-05-30", "回收"],
    },
    {
        "content": "2026年6月1日常备药：蒙脱石散。",
        "kind": "semantic",
        "cues": ["蒙脱石散"],
    },
    {
        "content": "2026年6月15日孩子腹泻，用蒙脱石散。",
        "kind": "episodic",
        "cues": ["2026-06-15", "腹泻"],
    },
    {
        "content": "2026年7月1日药箱整理：7 月 10 日。",
        "kind": "episodic",
        "cues": ["2026-07-01", "整理"],
    },
    {
        "content": "2026年7月10日整理完成。",
        "kind": "episodic",
        "cues": ["2026-07-10", "整理"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日买钙片。",
        "kind": "episodic",
        "cues": ["2026-08-01", "钙片"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日降压药快吃完。",
        "kind": "episodic",
        "cues": ["2026-08-05", "降压药"],
    },
    {
        "content": "药店电话 400-333-2222。",
        "kind": "semantic",
        "cues": ["药店", "电话"],
    },
    {
        "content": "药品储存：阴凉干燥处。",
        "kind": "semantic",
        "cues": ["储存"],
    },
]


QUESTIONS = [
    {
        "dim": "药箱清单",
        "q": "药箱里有什么？",
        "answer": "创可贴、体温计",
        "terms": ["体温计"],
    },
    {
        "dim": "感冒用药",
        "q": "感冒吃什么药？",
        "answer": "布洛芬",
        "terms": ["布洛芬"],
    },
    {
        "dim": "孩子退烧",
        "q": "孩子发烧用什么？",
        "answer": "美林",
        "terms": ["美林"],
    },
    {
        "dim": "过敏用药",
        "q": "过敏吃什么药？",
        "answer": "氯雷他定",
        "terms": ["氯雷他定"],
    },
    {
        "dim": "未来安排",
        "q": "下次买钙片是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "药品回收",
        "q": "过期药什么时候回收的？",
        "answer": "5月30日",
        "terms": ["30"],
    },
    {
        "dim": "腹泻用药",
        "q": "孩子腹泻用什么？",
        "answer": "蒙脱石散",
        "terms": ["蒙脱石散"],
    },
    {
        "dim": "药箱整理",
        "q": "药箱什么时候整理的？",
        "answer": "7月10日",
        "terms": ["10"],
    },
    {
        "dim": "药店电话",
        "q": "药店电话多少？",
        "answer": "400-333-2222",
        "terms": ["2222"],
    },
    {
        "dim": "药品储存",
        "q": "药品怎么储存？",
        "answer": "阴凉干燥处",
        "terms": ["阴凉"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭药箱",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="medicine_mem0db",
        out_name="medicine_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
