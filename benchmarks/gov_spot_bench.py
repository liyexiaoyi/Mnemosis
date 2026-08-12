"""Government & social-security spot-check (round 277): Mnemosis vs mem0."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月15日办社保卡：银行网点。",
        "kind": "episodic",
        "cues": ["2026-01-15", "社保卡"],
    },
    {
        "content": "2026年2月1日社保卡激活。",
        "kind": "episodic",
        "cues": ["2026-02-01", "社保卡"],
    },
    {
        "content": "2026年3月10日公积金提取申请：3 月 25 日到账。",
        "kind": "episodic",
        "cues": ["2026-03-10", "公积金"],
    },
    {
        "content": "2026年3月25日公积金到账 4.8 万。",
        "kind": "episodic",
        "cues": ["2026-03-25", "公积金"],
    },
    {
        "content": "2026年4月5日办居住证：材料提交。",
        "kind": "episodic",
        "cues": ["2026-04-05", "居住证"],
    },
    {
        "content": "2026年4月20日居住证下来，5 月 1 日领。",
        "kind": "episodic",
        "cues": ["2026-04-20", "居住证"],
    },
    {
        "content": "2026年5月1日领居住证。",
        "kind": "episodic",
        "cues": ["2026-05-01", "居住证"],
    },
    {
        "content": "2026年5月15日个税年度汇算：申请退税 1260 元。",
        "kind": "episodic",
        "cues": ["2026-05-15", "退税"],
    },
    {
        "content": "2026年5月30日退税到账 1260 元。",
        "kind": "episodic",
        "cues": ["2026-05-30", "退税"],
    },
    {
        "content": "2026年6月10日预约 6 月 20 日更换身份证。",
        "kind": "episodic",
        "cues": ["2026-06-10", "身份证"],
    },
    {
        "content": "2026年6月20日新身份证办好。",
        "kind": "episodic",
        "cues": ["2026-06-20", "身份证"],
    },
    {
        "content": "2026年7月1日医保异地备案：7 月 10 日生效。",
        "kind": "episodic",
        "cues": ["2026-07-01", "医保"],
    },
    {
        "content": "2026年7月10日医保备案生效。",
        "kind": "episodic",
        "cues": ["2026-07-10", "医保"],
    },
    {
        "content": "2026年7月15日孩子上户口：材料交派出所。",
        "kind": "episodic",
        "cues": ["2026-07-15", "户口"],
    },
    {
        "content": "2026年7月25日户口办完。",
        "kind": "episodic",
        "cues": ["2026-07-25", "户口"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日护照办理。",
        "kind": "episodic",
        "cues": ["2026-08-01", "护照"],
    },
    {
        "content": "2026年8月3日收到通知：8 月 15 日驾驶证换证。",
        "kind": "episodic",
        "cues": ["2026-08-03", "驾驶证"],
    },
    {
        "content": "2026年8月6日驾驶证体检预约 8 月 10 日。",
        "kind": "episodic",
        "cues": ["2026-08-06", "体检"],
    },
    {
        "content": "社保缴纳：每月 15 号前扣款。",
        "kind": "semantic",
        "cues": ["社保", "扣款"],
    },
    {
        "content": "公积金账号 110-223344。",
        "kind": "semantic",
        "cues": ["公积金", "账号"],
    },
    {
        "content": "社保客服 12333。",
        "kind": "semantic",
        "cues": ["社保", "电话"],
    },
    {
        "content": "政务大厅：周一到周五 9:00-17:00。",
        "kind": "semantic",
        "cues": ["政务大厅"],
    },
    {
        "content": "2026年8月8日预约 8 月 20 日车辆过户。",
        "kind": "episodic",
        "cues": ["2026-08-08", "过户"],
    },
    {
        "content": "户口本放保险柜。",
        "kind": "semantic",
        "cues": ["户口本"],
    },
]


QUESTIONS = [
    {
        "dim": "社保卡",
        "q": "社保卡什么时候激活的？",
        "answer": "2月1日",
        "terms": ["1"],
    },
    {
        "dim": "公积金",
        "q": "公积金提取到账多少？",
        "answer": "4.8万",
        "terms": ["4.8"],
    },
    {
        "dim": "居住证",
        "q": "居住证什么时候领的？",
        "answer": "5月1日",
        "terms": ["1"],
    },
    {
        "dim": "退税",
        "q": "退税退了多少钱？",
        "answer": "1260元",
        "terms": ["1260"],
    },
    {
        "dim": "身份证",
        "q": "新身份证什么时候办好的？",
        "answer": "6月20日",
        "terms": ["20"],
    },
    {
        "dim": "医保备案",
        "q": "医保备案什么时候生效？",
        "answer": "7月10日",
        "terms": ["10"],
    },
    {
        "dim": "户口办理",
        "q": "孩子户口办完了吗？",
        "answer": "7月25日办完",
        "terms": ["25"],
    },
    {
        "dim": "未来安排",
        "q": "下次护照办理是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "缴费规则",
        "q": "社保每月什么时候扣款？",
        "answer": "15号前",
        "terms": ["15"],
    },
    {
        "dim": "账号信息",
        "q": "公积金账号多少？",
        "answer": "110-223344",
        "terms": ["223344"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="政务社保",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="gov_mem0db",
        out_name="gov_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
