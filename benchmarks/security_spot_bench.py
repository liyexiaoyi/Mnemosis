"""Home-security spot-check (round 326): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日买监控摄像头。",
        "kind": "episodic",
        "cues": ["2026-01-10", "摄像头"],
    },
    {
        "content": "2026年1月20日装摄像头：门口。",
        "kind": "episodic",
        "cues": ["2026-01-20", "摄像头"],
    },
    {
        "content": "2026年2月1日买智能门锁。",
        "kind": "episodic",
        "cues": ["2026-02-01", "门锁"],
    },
    {
        "content": "2026年2月15日门锁安装。",
        "kind": "episodic",
        "cues": ["2026-02-15", "门锁"],
    },
    {
        "content": "2026年3月1日预约 3 月 15 日安防调试。",
        "kind": "episodic",
        "cues": ["2026-03-01", "调试"],
    },
    {
        "content": "2026年3月15日调试完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "调试"],
    },
    {
        "content": "2026年4月1日摄像头离线，4 月 5 日重启。",
        "kind": "episodic",
        "cues": ["2026-04-01", "离线"],
    },
    {
        "content": "2026年4月5日恢复。",
        "kind": "episodic",
        "cues": ["2026-04-05", "恢复"],
    },
    {
        "content": "2026年5月1日预约 5 月 15 日云存储续费。",
        "kind": "episodic",
        "cues": ["2026-05-01", "云存储"],
    },
    {
        "content": "2026年5月15日续费完成。",
        "kind": "episodic",
        "cues": ["2026-05-15", "云存储"],
    },
    {
        "content": "2026年6月1日门锁没电，6 月 5 日换电池。",
        "kind": "episodic",
        "cues": ["2026-06-01", "电池"],
    },
    {
        "content": "2026年6月5日换电池完成。",
        "kind": "episodic",
        "cues": ["2026-06-05", "电池"],
    },
    {
        "content": "2026年7月1日预约 7 月 15 日报警器测试。",
        "kind": "episodic",
        "cues": ["2026-07-01", "报警器"],
    },
    {
        "content": "2026年7月15日测试完成。",
        "kind": "episodic",
        "cues": ["2026-07-15", "报警器"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日换摄像头。",
        "kind": "episodic",
        "cues": ["2026-08-01", "摄像头"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日云存储到期。",
        "kind": "episodic",
        "cues": ["2026-08-05", "云存储"],
    },
    {
        "content": "安防客服 400-555-9999。",
        "kind": "semantic",
        "cues": ["客服", "电话"],
    },
    {
        "content": "摄像头密码 123456。",
        "kind": "semantic",
        "cues": ["摄像头", "密码"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日安防展。",
        "kind": "episodic",
        "cues": ["2026-08-08", "安防展"],
    },
]


QUESTIONS = [
    {
        "dim": "安防设备",
        "q": "买了什么安防设备？",
        "answer": "智能门锁",
        "terms": ["门锁"],
    },
    {
        "dim": "摄像头位置",
        "q": "摄像头装在哪？",
        "answer": "门口",
        "terms": ["门口"],
    },
    {
        "dim": "安防调试",
        "q": "安防什么时候调试的？",
        "answer": "3月15日",
        "terms": ["15"],
    },
    {
        "dim": "未来安排",
        "q": "下次换摄像头是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "门锁电池",
        "q": "门锁什么时候换电池的？",
        "answer": "6月5日",
        "terms": ["5"],
    },
    {
        "dim": "云存储",
        "q": "云存储什么时候续的？",
        "answer": "5月15日",
        "terms": ["15"],
    },
    {
        "dim": "报警器",
        "q": "报警器什么时候测试的？",
        "answer": "7月15日",
        "terms": ["15"],
    },
    {
        "dim": "安防客服",
        "q": "安防客服电话多少？",
        "answer": "400-555-9999",
        "terms": ["9999"],
    },
    {
        "dim": "摄像头密码",
        "q": "摄像头密码多少？",
        "answer": "123456",
        "terms": ["123456"],
    },
    {
        "dim": "云存储到期",
        "q": "云存储什么时候到期？",
        "answer": "8月15日",
        "terms": ["15"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭安防",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="security_mem0db",
        out_name="security_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
