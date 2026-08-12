"""Dental-orthodontics spot-check (round 293): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日第一次看牙：蛀牙两颗。",
        "kind": "episodic",
        "cues": ["2026-01-10", "看牙"],
    },
    {
        "content": "2026年1月20日补牙：1 月 25 日。",
        "kind": "episodic",
        "cues": ["2026-01-20", "补牙"],
    },
    {
        "content": "2026年1月25日补牙完成，花 800 元。",
        "kind": "episodic",
        "cues": ["2026-01-25", "补牙"],
    },
    {
        "content": "2026年2月1日洗牙预约：2 月 10 日。",
        "kind": "episodic",
        "cues": ["2026-02-01", "洗牙"],
    },
    {
        "content": "2026年2月10日洗牙完成。",
        "kind": "episodic",
        "cues": ["2026-02-10", "洗牙"],
    },
    {
        "content": "2026年3月1日咨询正畸：钢牙 1.2 万，隐形 2.4 万。",
        "kind": "semantic",
        "cues": ["正畸", "隐形"],
    },
    {
        "content": "2026年3月15日决定隐形正畸。",
        "kind": "episodic",
        "cues": ["2026-03-15", "隐形"],
    },
    {
        "content": "2026年4月1日取牙模。",
        "kind": "episodic",
        "cues": ["2026-04-01", "牙模"],
    },
    {
        "content": "2026年4月15日牙套到货，开始戴。",
        "kind": "episodic",
        "cues": ["2026-04-15", "牙套"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日复查。",
        "kind": "episodic",
        "cues": ["2026-05-01", "复查"],
    },
    {
        "content": "2026年5月15日复查：调整牙套。",
        "kind": "episodic",
        "cues": ["2026-05-15", "复查"],
    },
    {
        "content": "2026年6月1日牙套磨嘴，买正畸蜡。",
        "kind": "episodic",
        "cues": ["2026-06-01", "正畸蜡"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日拔智齿。",
        "kind": "episodic",
        "cues": ["2026-06-15", "智齿"],
    },
    {
        "content": "2026年6月25日拔智齿完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "智齿"],
    },
    {
        "content": "2026年7月1日复查预约：7 月 15 日。",
        "kind": "episodic",
        "cues": ["2026-07-01", "复查"],
    },
    {
        "content": "2026年7月15日复查完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "复查"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日换牙套。",
        "kind": "episodic",
        "cues": ["2026-08-01", "换牙套"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日复诊。",
        "kind": "episodic",
        "cues": ["2026-08-05", "复诊"],
    },
    {
        "content": "牙医电话 139-3333-4444。",
        "kind": "semantic",
        "cues": ["牙医", "电话"],
    },
    {
        "content": "正畸注意事项：吃完东西要刷牙。",
        "kind": "semantic",
        "cues": ["注意事项"],
    },
]


QUESTIONS = [
    {
        "dim": "补牙记录",
        "q": "补牙什么时候做的？花了多少钱？",
        "answer": "1月25日，800元",
        "terms": ["800"],
    },
    {
        "dim": "正畸方案",
        "q": "隐形正畸多少钱？",
        "answer": "2.4万",
        "terms": ["2.4"],
    },
    {
        "dim": "正畸进度",
        "q": "什么时候开始戴牙套？",
        "answer": "4月15日",
        "terms": ["15"],
    },
    {
        "dim": "未来安排",
        "q": "下次换牙套是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "复查记录",
        "q": "上次复查是什么时候？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "智齿记录",
        "q": "智齿什么时候拔的？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "正畸蜡",
        "q": "牙套磨嘴怎么办？",
        "answer": "买正畸蜡",
        "terms": ["正畸蜡"],
    },
    {
        "dim": "医生电话",
        "q": "牙医电话多少？",
        "answer": "139-3333-4444",
        "terms": ["4444"],
    },
    {
        "dim": "注意事项",
        "q": "正畸要注意什么？",
        "answer": "吃完东西要刷牙",
        "terms": ["刷牙"],
    },
    {
        "dim": "复诊提醒",
        "q": "什么时候复诊？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="口腔正畸",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="dental_mem0db",
        out_name="dental_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
