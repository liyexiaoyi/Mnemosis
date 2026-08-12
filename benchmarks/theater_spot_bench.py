"""Home-theater spot-check (round 315): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买投影仪：坚果 4599 元。",
        "kind": "episodic",
        "cues": ["2026-01-10", "投影仪"],
    },
    {
        "content": "2026年1月20日买幕布：100 寸。",
        "kind": "episodic",
        "cues": ["2026-01-20", "幕布"],
    },
    {
        "content": "2026年2月1日装投影仪。",
        "kind": "episodic",
        "cues": ["2026-02-01", "安装"],
    },
    {
        "content": "2026年2月15日音响接线。",
        "kind": "episodic",
        "cues": ["2026-02-15", "音响"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日调音。",
        "kind": "episodic",
        "cues": ["2026-03-01", "调音"],
    },
    {
        "content": "2026年3月15日调音完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "调音"],
    },
    {
        "content": "2026年4月1日投影仪灯泡变暗，4 月 10 日换。",
        "kind": "episodic",
        "cues": ["2026-04-01", "灯泡"],
    },
    {
        "content": "2026年4月10日换灯泡完成。",
        "kind": "episodic",
        "cues": ["2026-04-10", "灯泡"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日清洁镜头。",
        "kind": "episodic",
        "cues": ["2026-05-01", "镜头"],
    },
    {
        "content": "2026年5月15日清洁完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "镜头"],
    },
    {
        "content": "2026年6月1日买流媒体会员。",
        "kind": "episodic",
        "cues": ["2026-06-01", "会员"],
    },
    {
        "content": "2026年6月15日预约 6 月 25 日升级音响。",
        "kind": "episodic",
        "cues": ["2026-06-15", "音响"],
    },
    {
        "content": "2026年6月25日升级完成。",
        "kind": "episodic",
        "cues": ["2026-06-25", "音响"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日投影校准。",
        "kind": "episodic",
        "cues": ["2026-07-01", "校准"],
    },
    {
        "content": "2026年7月15日校准完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "校准"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日换幕布。",
        "kind": "episodic",
        "cues": ["2026-08-01", "幕布"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日会员续费。",
        "kind": "episodic",
        "cues": ["2026-08-05", "续费"],
    },
    {
        "content": "影音店电话 400-888-2222。",
        "kind": "semantic",
        "cues": ["影音店", "电话"],
    },
    {
        "content": "观影位置：沙发距离幕布 3 米。",
        "kind": "semantic",
        "cues": ["观影", "位置"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日家庭影院展。",
        "kind": "episodic",
        "cues": ["2026-08-08", "影院展"],
    },
]


QUESTIONS = [
    {
        "dim": "投影仪",
        "q": "投影仪多少钱？",
        "answer": "4599元",
        "terms": ["4599"],
    },
    {
        "dim": "灯泡更换",
        "q": "投影仪灯泡什么时候换的？",
        "answer": "4月10日",
        "terms": ["10"],
    },
    {
        "dim": "音响升级",
        "q": "音响什么时候升级的？",
        "answer": "6月25日",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次换幕布是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "投影校准",
        "q": "投影什么时候校准的？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "调音记录",
        "q": "调音什么时候完成的？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "观影距离",
        "q": "沙发离幕布多远？",
        "answer": "3米",
        "terms": ["3"],
    },
    {
        "dim": "影音店",
        "q": "影音店电话多少？",
        "answer": "400-888-2222",
        "terms": ["2222"],
    },
    {
        "dim": "会员续费",
        "q": "流媒体会员什么时候续费？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "影院展",
        "q": "家庭影院展什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭影院",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="theater_mem0db",
        out_name="theater_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
