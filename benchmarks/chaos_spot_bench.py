"""Chaos spot-check (round 364): Mnemosis vs mem0 ONLY.

10 chaos dimensions: out-of-order writes, near-duplicates, conflicting
facts, noisy/garbled records, missing fields, extreme length, confused
future dates, similar-entity interference, typos/colloquial speech, and
mixed Chinese/English/pinyin.
"""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    # Similar-entity interference: 老王修车店 vs 老王修理店
    {
        "content": "2026年5月20日 老王修理店(不是修车店)补胎，40元。",
        "kind": "episodic",
        "cues": ["2026-05-20", "补胎"],
    },
    {
        "content": "2026年1月6日 老王修车店换机油，280元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "机油"],
    },
    # Out-of-order: 2月8日 after 3月15日 on purpose
    {
        "content": "2026年3月15日 老王修车店换刹车片，费用450元。",
        "kind": "episodic",
        "cues": ["2026-03-15", "刹车片"],
    },
    {
        "content": "2026年2月8日 老王修车店换了电瓶，600元。",
        "kind": "episodic",
        "cues": ["2026-02-08", "电瓶"],
    },
    # Noisy record carrying the 雨刮器 price
    {
        "content": "2026年4月2日 哈哈哈 老王修车店 ！@#￥ 换了雨刮器 88元 啦啦啦 🚗",
        "kind": "episodic",
        "cues": ["2026-04-02", "雨刮器"],
    },
    # Conflicting facts: property fee (latest wins)
    {
        "content": "2026年1月6日 缴纳物业费一年2400元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "物业费"],
    },
    {
        "content": "2026年7月1日 物业费调整为一年3000元。",
        "kind": "episodic",
        "cues": ["2026-07-01", "物业费"],
    },
    # Conflicting facts: opening hours (latest wins)
    {
        "content": "2026年2月10日 老王修车店营业时间 早9点到晚6点。",
        "kind": "semantic",
        "cues": ["营业时间", "9点"],
    },
    {
        "content": "2026年6月1日 老王修车店营业时间改为早8点到晚8点。",
        "kind": "semantic",
        "cues": ["营业时间", "8点"],
    },
    # Missing amount decoy for the 雨刮器 question
    {
        "content": "2026年5月30日 老王修车店更换雨刮器。",
        "kind": "episodic",
        "cues": ["2026-05-30", "雨刮器"],
    },
    # Future-dated events (next = 10月8日)
    {
        "content": "2026年9月20日 预约10月8日换轮胎。",
        "kind": "episodic",
        "cues": ["2026-09-20", "换轮胎"],
    },
    {
        "content": "2026年10月1日 国庆后恢复营业。",
        "kind": "episodic",
        "cues": ["2026-10-01", "国庆"],
    },
    # Near-duplicate of the 刹车片 event (latest = 7月3日)
    {
        "content": "2026年7月3日 老王修车店更换刹车片，450元。",
        "kind": "episodic",
        "cues": ["2026-07-03", "刹车片"],
    },
    # Typo + colloquial: 修里 / 昨儿个
    {
        "content": "2026年6月12日 昨儿个老王修车店修里了空调，花了350元。",
        "kind": "episodic",
        "cues": ["2026-06-12", "空调"],
    },
    # Mixed Chinese/English
    {
        "content": "2026年5月1日 老王修车店 WiFi 升级，费用120元。",
        "kind": "episodic",
        "cues": ["2026-05-01", "WiFi"],
    },
    # Pinyin
    {
        "content": "2026年8月5日 老王修车店 YueFei 年检代办，费用200元。",
        "kind": "episodic",
        "cues": ["2026-08-05", "年检"],
    },
    # English date format
    {
        "content": "2026-08-08 老王修车店 四轮定位，150元。",
        "kind": "episodic",
        "cues": ["2026-08-08", "四轮定位"],
    },
    # Mixed English word
    {
        "content": "2026年7月25日 老王修车店 换 battery，300元。",
        "kind": "episodic",
        "cues": ["2026-07-25", "battery"],
    },
    # Garbled noise
    {
        "content": "#@老王修车店 2026年3月28日 洗车 50元 asdfgh",
        "kind": "episodic",
        "cues": ["2026-03-28", "洗车"],
    },
    # Extreme short
    {
        "content": "修车。",
        "kind": "episodic",
        "cues": ["修车"],
    },
    # Extreme long
    {
        "content": (
            "2026年4月18日 老王修车店给车打了个蜡，80块。"
            "顺便检查了胎压、玻璃水、雨刮器胶条，还帮忙清理了发动机舱，"
            "师傅说下次记得提前预约，周末人多要排队大概四十分钟，"
            "如果赶时间可以工作日中午来，人少一些。"
        ),
        "kind": "episodic",
        "cues": ["2026-04-18", "打蜡"],
    },
    # Decoy full inspection record
    {
        "content": "2026年6月30日 老王修车店 做了一次全车检查 100元 ！！",
        "kind": "episodic",
        "cues": ["2026-06-30", "全车检查"],
    },
    # Phone record (no date)
    {
        "content": "老王修车店 电话 138-0000-0000。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    # Confusing future "上次" trap
    {
        "content": "2026年11月1日 老王修车店 冬季保养预约。",
        "kind": "episodic",
        "cues": ["2026-11-01", "冬季保养"],
    },
]


QUESTIONS = [
    {
        "dim": "冲突-最新费用",
        "q": "现在物业费一年多少钱？",
        "answer": "3000元",
        "terms": ["3000"],
    },
    {
        "dim": "未来安排",
        "q": "下次换轮胎是什么时候？",
        "answer": "10月8日",
        "terms": ["8"],
    },
    {
        "dim": "冲突-最新营业时间",
        "q": "老王修车店现在几点开门？",
        "answer": "早8点",
        "terms": ["8"],
    },
    {
        "dim": "噪声记录",
        "q": "雨刮器多少钱？",
        "answer": "88元",
        "terms": ["88"],
    },
    {
        "dim": "英文日期",
        "q": "四轮定位什么时候做的？",
        "answer": "8月8日",
        "terms": ["8"],
    },
    {
        "dim": "中英混合",
        "q": "换电池多少钱？",
        "answer": "300元",
        "terms": ["300"],
    },
    {
        "dim": "拼音",
        "q": "年检代办多少钱？",
        "answer": "200元",
        "terms": ["200"],
    },
    {
        "dim": "重复近似",
        "q": "上次换刹车片是什么时候？",
        "answer": "7月3日",
        "terms": ["3"],
    },
    {
        "dim": "错别字口语",
        "q": "空调什么时候修的？",
        "answer": "6月12日",
        "terms": ["12"],
    },
    {
        "dim": "缺失字段",
        "q": "老王修车店电话多少？",
        "answer": "138-0000-0000",
        "terms": ["0000"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="混乱场景",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="chaos_mem0db",
        out_name="chaos_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
