"""Baby-care spot-check (round 269): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2025年11月20日小宝出生：3.4kg，50cm。",
        "kind": "episodic",
        "cues": ["2025-11-20", "出生"],
    },
    {
        "content": "2025年12月10日满月体检：黄疸退了。",
        "kind": "episodic",
        "cues": ["2025-12-10", "体检"],
    },
    {
        "content": "2026年1月15日打乙肝第二针。",
        "kind": "episodic",
        "cues": ["2026-01-15", "乙肝"],
    },
    {
        "content": "2026年2月10日小宝体重 5.6kg。",
        "kind": "episodic",
        "cues": ["2026-02-10", "体重"],
    },
    {
        "content": "2026年3月5日预约 3 月 20 日三个月体检。",
        "kind": "episodic",
        "cues": ["2026-03-05", "体检"],
    },
    {
        "content": "2026年3月20日三个月体检：体重 6.8kg，身高 62cm。",
        "kind": "episodic",
        "cues": ["2026-03-20", "体检"],
    },
    {
        "content": "2026年4月10日打百白破第一针。",
        "kind": "episodic",
        "cues": ["2026-04-10", "百白破"],
    },
    {
        "content": "2026年4月25日开始吃辅食：米粉。",
        "kind": "episodic",
        "cues": ["2026-04-25", "辅食"],
    },
    {
        "content": "2026年5月10日添加南瓜泥。",
        "kind": "episodic",
        "cues": ["2026-05-10", "南瓜"],
    },
    {
        "content": "2026年6月1日预约 6 月 15 日六月体检。",
        "kind": "episodic",
        "cues": ["2026-06-01", "体检"],
    },
    {
        "content": "2026年6月15日六月体检：体重 8.1kg。",
        "kind": "episodic",
        "cues": ["2026-06-15", "体检"],
    },
    {
        "content": "2026年6月25日打乙肝第三针。",
        "kind": "episodic",
        "cues": ["2026-06-25", "乙肝"],
    },
    {
        "content": "2026年7月5日小宝发烧 38.5 度，7 月 7 日退烧。",
        "kind": "episodic",
        "cues": ["2026-07-05", "发烧"],
    },
    {
        "content": "2026年7月15日幼儿园开放日报名：8 月 2 日参观。",
        "kind": "episodic",
        "cues": ["2026-07-15", "幼儿园"],
    },
    {
        "content": "2026年7月20日买婴儿保险：年缴 3200 元。",
        "kind": "episodic",
        "cues": ["2026-07-20", "保险"],
    },
    {
        "content": "2026年7月25日预约 8 月 10 日儿科复诊。",
        "kind": "episodic",
        "cues": ["2026-07-25", "复诊"],
    },
    {
        "content": "2026年8月2日幼儿园开放日：老师说要 9 月 1 日入学。",
        "kind": "episodic",
        "cues": ["2026-08-02", "幼儿园"],
    },
    {
        "content": "2026年8月5日添加鸡蛋黄，观察过敏。",
        "kind": "episodic",
        "cues": ["2026-08-05", "鸡蛋黄"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日交幼儿园材料。",
        "kind": "episodic",
        "cues": ["2026-08-08", "幼儿园"],
    },
    {
        "content": "玩具安全记录：积木 3cm 以上。",
        "kind": "semantic",
        "cues": ["玩具", "安全"],
    },
    {
        "content": "睡眠记录：晚上 9 点睡，白天两觉。",
        "kind": "semantic",
        "cues": ["睡眠", "9点"],
    },
    {
        "content": "辅食禁忌：一岁前不吃蜂蜜。",
        "kind": "semantic",
        "cues": ["禁忌", "蜂蜜"],
    },
    {
        "content": "保险客服电话 400-123-4567。",
        "kind": "semantic",
        "cues": ["保险", "电话"],
    },
    {
        "content": "疫苗本放床头柜。",
        "kind": "semantic",
        "cues": ["疫苗本"],
    },
    {
        "content": "2026年8月9日预约 8 月 16 日拍百天照。",
        "kind": "episodic",
        "cues": ["2026-08-09", "拍照"],
    },
]


QUESTIONS = [
    {
        "dim": "出生信息",
        "q": "小宝出生时多重？",
        "answer": "3.4kg",
        "terms": ["3.4"],
    },
    {
        "dim": "体检记录",
        "q": "上次体检是什么时候？体重多少？",
        "answer": "6月15日，8.1kg",
        "terms": ["8.1"],
    },
    {
        "dim": "疫苗记录",
        "q": "上次打疫苗是什么时候？打的什么？",
        "answer": "6月25日，乙肝第三针",
        "terms": ["乙肝"],
    },
    {
        "dim": "未来安排",
        "q": "下次儿科复诊是什么时候？",
        "answer": "8月10日",
        "terms": ["10"],
    },
    {
        "dim": "辅食记录",
        "q": "现在辅食加了什么？",
        "answer": "米粉、南瓜泥、鸡蛋黄",
        "terms": ["鸡蛋黄"],
    },
    {
        "dim": "幼儿园",
        "q": "幼儿园什么时候入学？材料什么时候交？",
        "answer": "9月1日入学，8月20日交材料",
        "terms": ["20", "1"],
    },
    {
        "dim": "保险信息",
        "q": "婴儿保险多少钱一年？客服电话多少？",
        "answer": "3200元，400-123-4567",
        "terms": ["3200", "400"],
    },
    {
        "dim": "发烧记录",
        "q": "小宝上次发烧什么时候退的？",
        "answer": "7月7日",
        "terms": ["7"],
    },
    {
        "dim": "睡眠记录",
        "q": "小宝晚上几点睡？",
        "answer": "9点",
        "terms": ["9"],
    },
    {
        "dim": "安全禁忌",
        "q": "一岁前不能吃什么？",
        "answer": "蜂蜜",
        "terms": ["蜂蜜"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="育儿护理",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="baby_mem0db",
        out_name="baby_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
