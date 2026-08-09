"""Pet-boarding spot-check (round 282): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日找宠物寄养店：阳光宠物之家。",
        "kind": "episodic",
        "cues": ["2026-01-10", "寄养"],
    },
    {
        "content": "2026年1月15日参观寄养店，环境不错。",
        "kind": "episodic",
        "cues": ["2026-01-15", "参观"],
    },
    {
        "content": "2026年2月1日第一次寄养：2 月 5 日到 2 月 8 日。",
        "kind": "episodic",
        "cues": ["2026-02-01", "寄养"],
    },
    {
        "content": "2026年2月5日送猫去寄养，带猫粮和猫砂。",
        "kind": "episodic",
        "cues": ["2026-02-05", "寄养"],
    },
    {
        "content": "2026年2月8日接猫回家，状态很好。",
        "kind": "episodic",
        "cues": ["2026-02-08", "接猫"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日寄养。",
        "kind": "episodic",
        "cues": ["2026-03-01", "寄养"],
    },
    {
        "content": "2026年3月15日寄养 3 天，费用 150 元/天。",
        "kind": "episodic",
        "cues": ["2026-03-15", "寄养"],
    },
    {
        "content": "2026年4月1日寄养店要求疫苗本。",
        "kind": "semantic",
        "cues": ["疫苗本"],
    },
    {
        "content": "2026年4月10日带猫打疫苗：4 月 15 日补打第三针。",
        "kind": "episodic",
        "cues": ["2026-04-10", "疫苗"],
    },
    {
        "content": "2026年4月15日打疫苗完成。",
        "kind": "episodic",
        "cues": ["2026-04-15", "疫苗"],
    },
    {
        "content": "2026年5月1日寄养店涨价：180 元/天。",
        "kind": "episodic",
        "cues": ["2026-05-01", "涨价"],
    },
    {
        "content": "2026年5月20日预约 5 月 30 日寄养。",
        "kind": "episodic",
        "cues": ["2026-05-20", "寄养"],
    },
    {
        "content": "2026年5月30日寄养 4 天。",
        "kind": "episodic",
        "cues": ["2026-05-30", "寄养"],
    },
    {
        "content": "2026年6月1日接猫，寄养后猫瘦了 0.3kg。",
        "kind": "episodic",
        "cues": ["2026-06-01", "接猫"],
    },
    {
        "content": "2026年6月10日换寄养店：猫语时光。",
        "kind": "semantic",
        "cues": ["猫语时光"],
    },
    {
        "content": "2026年6月20日参观猫语时光，有监控。",
        "kind": "episodic",
        "cues": ["2026-06-20", "参观"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日寄养。",
        "kind": "episodic",
        "cues": ["2026-07-01", "寄养"],
    },
    {
        "content": "2026年7月10日寄养 5 天，费用 200 元/天。",
        "kind": "episodic",
        "cues": ["2026-07-10", "寄养"],
    },
    {
        "content": "2026年7月15日接猫，状态好，有每日视频。",
        "kind": "episodic",
        "cues": ["2026-07-15", "接猫"],
    },
    {
        "content": "2026年7月20日寄养店要求签协议。",
        "kind": "semantic",
        "cues": ["协议"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日寄养。",
        "kind": "episodic",
        "cues": ["2026-08-01", "寄养"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 10 日前交疫苗本复印件。",
        "kind": "episodic",
        "cues": ["2026-08-05", "疫苗本"],
    },
    {
        "content": "紧急联系：猫语时光 400-777-8888。",
        "kind": "semantic",
        "cues": ["电话", "猫语时光"],
    },
    {
        "content": "猫粮品牌：渴望鸡肉味。",
        "kind": "semantic",
        "cues": ["猫粮", "渴望"],
    },
    {
        "content": "猫的习惯：怕生，前 2 天躲床底。",
        "kind": "semantic",
        "cues": ["习惯", "怕生"],
    },
]


QUESTIONS = [
    {
        "dim": "寄养店铺",
        "q": "现在去哪家寄养？",
        "answer": "猫语时光",
        "terms": ["猫语时光"],
    },
    {
        "dim": "寄养费用",
        "q": "现在寄养一天多少钱？",
        "answer": "200元",
        "terms": ["200"],
    },
    {
        "dim": "寄养记录",
        "q": "上次寄养是什么时候？状态如何？",
        "answer": "7月10日，状态好",
        "terms": ["状态"],
    },
    {
        "dim": "未来安排",
        "q": "下次寄养是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "疫苗记录",
        "q": "疫苗什么时候补打的？",
        "answer": "4月15日",
        "terms": ["15"],
    },
    {
        "dim": "猫粮品牌",
        "q": "猫吃什么猫粮？",
        "answer": "渴望鸡肉味",
        "terms": ["渴望"],
    },
    {
        "dim": "紧急联系",
        "q": "寄养店电话多少？",
        "answer": "400-777-8888",
        "terms": ["8888"],
    },
    {
        "dim": "猫咪习惯",
        "q": "猫有什么习惯？",
        "answer": "怕生，躲床底",
        "terms": ["怕生"],
    },
    {
        "dim": "体重变化",
        "q": "上次寄养后体重怎么了？",
        "answer": "瘦了0.3kg",
        "terms": ["0.3"],
    },
    {
        "dim": "寄养材料",
        "q": "寄养要交什么？",
        "answer": "疫苗本复印件",
        "terms": ["疫苗本"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="宠物寄养",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="boarding_mem0db",
        out_name="boarding_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
