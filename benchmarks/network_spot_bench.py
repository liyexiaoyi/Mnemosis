"""Home-network spot-check (round 311): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日装宽带：500M。",
        "kind": "episodic",
        "cues": ["2026-01-10", "宽带"],
    },
    {
        "content": "2026年1月20日买路由器：WiFi7。",
        "kind": "episodic",
        "cues": ["2026-01-20", "路由器"],
    },
    {
        "content": "2026年2月1日网速测试：480M。",
        "kind": "episodic",
        "cues": ["2026-02-01", "测速"],
    },
    {
        "content": "2026年2月15日信号死角：卧室。",
        "kind": "semantic",
        "cues": ["信号", "卧室"],
    },
    {
        "content": "2026年3月1日买 Mesh 子路由。",
        "kind": "episodic",
        "cues": ["2026-03-01", "Mesh"],
    },
    {
        "content": "2026年3月15日组网完成。",
        "kind": "episodic",
        "cues": ["2026-03-15", "组网"],
    },
    {
        "content": "2026年4月1日预约 4 月 15 日升级千兆。",
        "kind": "episodic",
        "cues": ["2026-04-01", "千兆"],
    },
    {
        "content": "2026年4月15日升级完成。",
        "kind": "episodic",
        "cues": ["2026-04-15", "千兆"],
    },
    {
        "content": "2026年5月1日网费：每月 199 元。",
        "kind": "semantic",
        "cues": ["网费", "199"],
    },
    {
        "content": "2026年5月20日预约 6 月 1 日换光猫。",
        "kind": "episodic",
        "cues": ["2026-05-20", "光猫"],
    },
    {
        "content": "2026年6月1日光猫换好。",
        "kind": "episodic",
        "cues": ["2026-06-01", "光猫"],
    },
    {
        "content": "2026年7月1日断网，7 月 3 日恢复。",
        "kind": "episodic",
        "cues": ["2026-07-01", "断网"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日布线。",
        "kind": "episodic",
        "cues": ["2026-07-15", "布线"],
    },
    {
        "content": "2026年7月25日布线完成。",
        "kind": "episodic",
        "cues": ["2026-07-25", "布线"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日测速。",
        "kind": "episodic",
        "cues": ["2026-08-01", "测速"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日交网费。",
        "kind": "episodic",
        "cues": ["2026-08-05", "网费"],
    },
    {
        "content": "宽带客服 10000。",
        "kind": "semantic",
        "cues": ["宽带", "电话"],
    },
    {
        "content": "Wi-Fi 密码：home2026。",
        "kind": "semantic",
        "cues": ["Wi-Fi", "密码"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日免费提速。",
        "kind": "episodic",
        "cues": ["2026-08-08", "提速"],
    },
]


QUESTIONS = [
    {
        "dim": "宽带速率",
        "q": "现在宽带多少兆？",
        "answer": "千兆",
        "terms": ["千兆"],
    },
    {
        "dim": "网速记录",
        "q": "上次测速多少？",
        "answer": "480M",
        "terms": ["480"],
    },
    {
        "dim": "信号问题",
        "q": "哪里信号不好？",
        "answer": "卧室",
        "terms": ["卧室"],
    },
    {
        "dim": "未来安排",
        "q": "下次测速是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "网费",
        "q": "网费一个月多少钱？",
        "answer": "199元",
        "terms": ["199"],
    },
    {
        "dim": "光猫更换",
        "q": "光猫什么时候换的？",
        "answer": "6月1日",
        "terms": ["1"],
    },
    {
        "dim": "断网恢复",
        "q": "断网什么时候恢复的？",
        "answer": "7月3日",
        "terms": ["3"],
    },
    {
        "dim": "Wi-Fi密码",
        "q": "Wi-Fi密码多少？",
        "answer": "home2026",
        "terms": ["home"],
    },
    {
        "dim": "宽带客服",
        "q": "宽带客服电话多少？",
        "answer": "10000",
        "terms": ["10000"],
    },
    {
        "dim": "免费提速",
        "q": "免费提速什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭网络",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="network_mem0db",
        out_name="network_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
