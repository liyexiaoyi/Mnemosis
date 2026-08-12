"""Home-safe spot-check (round 339): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月13日购买家庭保险柜，价格2600元。",
        "kind": "episodic",
        "cues": ["2026-01-13", "保险柜"],
    },
    {
        "content": "2026年1月20日师傅上门安装保险柜。",
        "kind": "episodic",
        "cues": ["2026-01-20", "安装"],
    },
    {
        "content": "保险柜位置：主卧衣柜内。",
        "kind": "semantic",
        "cues": ["位置", "主卧"],
    },
    {
        "content": "2026年1月25日设置指纹开锁，录入2个指纹。",
        "kind": "episodic",
        "cues": ["2026-01-25", "指纹"],
    },
    {
        "content": "售后电话 400-800-1234。",
        "kind": "semantic",
        "cues": ["售后", "电话"],
    },
    {
        "content": "2026年2月8日存放房产证和户口本。",
        "kind": "episodic",
        "cues": ["2026-02-08", "保险柜", "存放"],
    },
    {
        "content": "2026年2月20日购买保险柜防盗保险，年费120元。",
        "kind": "episodic",
        "cues": ["2026-02-20", "保险"],
    },
    {
        "content": "2026年3月5日收到通知：3月18日免费巡检。",
        "kind": "episodic",
        "cues": ["2026-03-05", "巡检"],
    },
    {
        "content": "2026年3月18日巡检完成，锁具正常。",
        "kind": "episodic",
        "cues": ["2026-03-18", "巡检"],
    },
    {
        "content": "2026年4月2日更换电池，提示低电量。",
        "kind": "episodic",
        "cues": ["2026-04-02", "电池"],
    },
    {
        "content": "2026年4月20日收到通知：5月8日保险柜使用培训。",
        "kind": "episodic",
        "cues": ["2026-04-20", "培训"],
    },
    {
        "content": "2026年5月8日培训完成。",
        "kind": "episodic",
        "cues": ["2026-05-08", "培训"],
    },
    {
        "content": "2026年5月20日存放存折和首饰盒。",
        "kind": "episodic",
        "cues": ["2026-05-20", "保险柜", "存放"],
    },
    {
        "content": "2026年6月1日预约6月14日搬家转移保险柜。",
        "kind": "episodic",
        "cues": ["2026-06-01", "搬家"],
    },
    {
        "content": "2026年6月14日保险柜转移到新家书房。",
        "kind": "episodic",
        "cues": ["2026-06-14", "搬家"],
    },
    {
        "content": "保险柜承重说明：最大承重80公斤。",
        "kind": "semantic",
        "cues": ["承重", "80"],
    },
    {
        "content": "2026年7月3日收到通知：7月19日指纹模块升级。",
        "kind": "episodic",
        "cues": ["2026-07-03", "升级"],
    },
    {
        "content": "2026年7月19日升级完成。",
        "kind": "episodic",
        "cues": ["2026-07-19", "升级"],
    },
    {
        "content": "2026年8月2日预约8月16日防盗保险续费。",
        "kind": "episodic",
        "cues": ["2026-08-02", "续费"],
    },
    {
        "content": "2026年8月10日收到提醒：8月22日电池更换周期。",
        "kind": "episodic",
        "cues": ["2026-08-10", "电池"],
    },
]


QUESTIONS = [
    {
        "dim": "购买时间",
        "q": "保险柜第一次什么时候买的？",
        "answer": "1月13日",
        "terms": ["13"],
    },
    {
        "dim": "价格",
        "q": "保险柜多少钱？",
        "answer": "2600元",
        "terms": ["2600"],
    },
    {
        "dim": "下次服务",
        "q": "下次保险柜服务是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "安装时间",
        "q": "保险柜什么时候安装的？",
        "answer": "1月20日",
        "terms": ["20"],
    },
    {
        "dim": "售后电话",
        "q": "保险柜售后电话多少？",
        "answer": "400-800-1234",
        "terms": ["1234"],
    },
    {
        "dim": "保险柜位置",
        "q": "保险柜放在哪里？",
        "answer": "主卧衣柜内",
        "terms": ["主卧"],
    },
    {
        "dim": "防盗保险",
        "q": "防盗保险一年多少钱？",
        "answer": "120元",
        "terms": ["120"],
    },
    {
        "dim": "存放物品",
        "q": "保险柜里放了哪些重要物品？",
        "answer": "房产证、户口本、存折、首饰盒",
        "terms": ["房产证"],
    },
    {
        "dim": "搬家转移",
        "q": "保险柜什么时候搬到新家的？",
        "answer": "6月14日",
        "terms": ["14"],
    },
    {
        "dim": "承重",
        "q": "保险柜最大承重多少？",
        "answer": "80公斤",
        "terms": ["80"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭保险柜",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="safe_mem0db",
        out_name="safe_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
