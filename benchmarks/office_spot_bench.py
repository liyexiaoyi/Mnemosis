"""Office-admin spot-check (round 290): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日办公室搬迁：新址科技园 B 座。",
        "kind": "episodic",
        "cues": ["2026-01-10", "搬迁"],
    },
    {
        "content": "2026年1月20日工位分配：小李 3 楼 A 区。",
        "kind": "semantic",
        "cues": ["工位", "小李"],
    },
    {
        "content": "2026年2月1日打印机采购：兄弟 2899 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "打印机"],
    },
    {
        "content": "2026年2月15日会议室预约规则：提前一天。",
        "kind": "semantic",
        "cues": ["会议室"],
    },
    {
        "content": "2026年3月1日门禁卡补办：3 月 5 日拿到。",
        "kind": "episodic",
        "cues": ["2026-03-01", "门禁卡"],
    },
    {
        "content": "2026年3月5日拿到门禁卡。",
        "kind": "episodic",
        "cues": ["2026-03-05", "门禁卡"],
    },
    {
        "content": "2026年4月1日空调报修：4 月 3 日修好。",
        "kind": "episodic",
        "cues": ["2026-04-01", "空调"],
    },
    {
        "content": "2026年4月3日空调修好。",
        "kind": "episodic",
        "cues": ["2026-04-03", "空调"],
    },
    {
        "content": "2026年5月1日预约 5 月 10 日消防演练。",
        "kind": "episodic",
        "cues": ["2026-05-01", "消防"],
    },
    {
        "content": "2026年5月10日消防演练完成。",
        "kind": "episodic",
        "cues": ["2026-05-10", "消防"],
    },
    {
        "content": "2026年6月1日办公用品盘点：缺 A4 纸。",
        "kind": "episodic",
        "cues": ["2026-06-01", "盘点"],
    },
    {
        "content": "2026年6月10日补购 A4 纸。",
        "kind": "episodic",
        "cues": ["2026-06-10", "A4"],
    },
    {
        "content": "2026年7月1日新同事入职，配电脑。",
        "kind": "episodic",
        "cues": ["2026-07-01", "入职"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日搬工位。",
        "kind": "episodic",
        "cues": ["2026-07-15", "搬工位"],
    },
    {
        "content": "2026年7月25日搬工位完成。",
        "kind": "episodic",
        "cues": ["2026-07-25", "搬工位"],
    },
    {
        "content": "2026年8月1日物业通知：8 月 10 日电梯检修。",
        "kind": "episodic",
        "cues": ["2026-08-01", "电梯"],
    },
    {
        "content": "2026年8月5日预约 8 月 15 日会议室。",
        "kind": "episodic",
        "cues": ["2026-08-05", "会议室"],
    },
    {
        "content": "办公室 Wi-Fi 密码 office2026。",
        "kind": "semantic",
        "cues": ["Wi-Fi", "密码"],
    },
    {
        "content": "物业电话 400-555-6666。",
        "kind": "semantic",
        "cues": ["物业", "电话"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日团建。",
        "kind": "episodic",
        "cues": ["2026-08-08", "团建"],
    },
]


QUESTIONS = [
    {
        "dim": "办公地址",
        "q": "办公室在哪？",
        "answer": "科技园B座",
        "terms": ["科技园"],
    },
    {
        "dim": "工位分配",
        "q": "小李工位在哪？",
        "answer": "3楼A区",
        "terms": ["A区"],
    },
    {
        "dim": "设备采购",
        "q": "打印机多少钱？",
        "answer": "2899元",
        "terms": ["2899"],
    },
    {
        "dim": "门禁卡",
        "q": "门禁卡什么时候拿到的？",
        "answer": "3月5日",
        "terms": ["5"],
    },
    {
        "dim": "空调维修",
        "q": "空调什么时候修好的？",
        "answer": "4月3日",
        "terms": ["3"],
    },
    {
        "dim": "未来安排",
        "q": "下次电梯检修是什么时候？",
        "answer": "8月10日",
        "terms": ["10"],
    },
    {
        "dim": "办公盘点",
        "q": "上次盘点缺什么？",
        "answer": "A4纸",
        "terms": ["A4"],
    },
    {
        "dim": "Wi-Fi密码",
        "q": "Wi-Fi密码多少？",
        "answer": "office2026",
        "terms": ["office"],
    },
    {
        "dim": "物业电话",
        "q": "物业电话多少？",
        "answer": "400-555-6666",
        "terms": ["6666"],
    },
    {
        "dim": "团建通知",
        "q": "团建什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="办公室行政",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="office_mem0db",
        out_name="office_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
