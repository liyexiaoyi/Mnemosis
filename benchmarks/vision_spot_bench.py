"""Eyeglasses & vision-care spot-check (round 281): Mnemosis vs mem0."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日视力检查：左眼 4.8，右眼 4.9。",
        "kind": "episodic",
        "cues": ["2026-01-10", "视力"],
    },
    {
        "content": "2026年1月15日配眼镜：镜片 1.67 折射率，镜架 899 元。",
        "kind": "episodic",
        "cues": ["2026-01-15", "配镜"],
    },
    {
        "content": "2026年2月1日取眼镜：总价 1680 元。",
        "kind": "episodic",
        "cues": ["2026-02-01", "取镜"],
    },
    {
        "content": "2026年2月10日戴新眼镜头晕，2 月 12 日回店调整。",
        "kind": "episodic",
        "cues": ["2026-02-10", "调整"],
    },
    {
        "content": "2026年3月1日隐形眼镜：月抛，每盒 89 元。",
        "kind": "semantic",
        "cues": ["隐形眼镜", "89"],
    },
    {
        "content": "2026年3月15日第一次戴隐形眼镜。",
        "kind": "episodic",
        "cues": ["2026-03-15", "隐形"],
    },
    {
        "content": "2026年4月1日眼干，买人工泪液。",
        "kind": "episodic",
        "cues": ["2026-04-01", "眼干"],
    },
    {
        "content": "2026年5月1日复查视力：双眼 5.0。",
        "kind": "episodic",
        "cues": ["2026-05-01", "复查"],
    },
    {
        "content": "2026年5月15日预约 5 月 25 日验光。",
        "kind": "episodic",
        "cues": ["2026-05-15", "验光"],
    },
    {
        "content": "2026年5月25日验光：度数没变。",
        "kind": "episodic",
        "cues": ["2026-05-25", "验光"],
    },
    {
        "content": "2026年6月1日换镜片：防蓝光。",
        "kind": "episodic",
        "cues": ["2026-06-01", "防蓝光"],
    },
    {
        "content": "2026年6月15日眼镜腿松，6 月 18 日修好。",
        "kind": "episodic",
        "cues": ["2026-06-15", "镜腿"],
    },
    {
        "content": "2026年7月1日预约 7 月 10 日眼底检查。",
        "kind": "episodic",
        "cues": ["2026-07-01", "眼底"],
    },
    {
        "content": "2026年7月10日眼底检查正常。",
        "kind": "episodic",
        "cues": ["2026-07-10", "眼底"],
    },
    {
        "content": "2026年7月20日隐形眼镜用完，7 月 25 日再买。",
        "kind": "episodic",
        "cues": ["2026-07-20", "隐形"],
    },
    {
        "content": "2026年7月25日买隐形眼镜 3 盒。",
        "kind": "episodic",
        "cues": ["2026-07-25", "隐形"],
    },
    {
        "content": "2026年8月1日眼睛痒，8 月 3 日看医生。",
        "kind": "episodic",
        "cues": ["2026-08-01", "眼睛"],
    },
    {
        "content": "2026年8月3日看医生：结膜炎，开药。",
        "kind": "episodic",
        "cues": ["2026-08-03", "结膜炎"],
    },
    {
        "content": "2026年8月5日预约 8 月 15 日复查眼睛。",
        "kind": "episodic",
        "cues": ["2026-08-05", "复查"],
    },
    {
        "content": "视力处方：右 -2.00，左 -1.75。",
        "kind": "semantic",
        "cues": ["处方"],
    },
    {
        "content": "眼镜清洗：用洗镜液，不用纸巾。",
        "kind": "semantic",
        "cues": ["清洗"],
    },
    {
        "content": "眼科医院：市二院眼科。",
        "kind": "semantic",
        "cues": ["医院", "市二院"],
    },
    {
        "content": "医生叮嘱：少看手机，多望远。",
        "kind": "semantic",
        "cues": ["叮嘱"],
    },
    {
        "content": "2026年8月8日收到提醒：8 月 20 日眼镜保养。",
        "kind": "episodic",
        "cues": ["2026-08-08", "保养"],
    },
]


QUESTIONS = [
    {
        "dim": "视力检查",
        "q": "上次视力检查是什么时候？双眼多少？",
        "answer": "5月1日，双眼5.0",
        "terms": ["5.0"],
    },
    {
        "dim": "配镜信息",
        "q": "眼镜总价多少？镜架多少钱？",
        "answer": "1680元，镜架899元",
        "terms": ["1680", "899"],
    },
    {
        "dim": "视力处方",
        "q": "视力处方是多少？",
        "answer": "右-2.00，左-1.75",
        "terms": ["-2.00"],
    },
    {
        "dim": "隐形眼镜",
        "q": "隐形眼镜多少钱一盒？",
        "answer": "89元",
        "terms": ["89"],
    },
    {
        "dim": "未来安排",
        "q": "下次复查眼睛是什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "就诊记录",
        "q": "上次看医生是什么时候？什么病？",
        "answer": "8月3日，结膜炎",
        "terms": ["结膜炎"],
    },
    {
        "dim": "当前镜片",
        "q": "现在镜片是什么？",
        "answer": "防蓝光",
        "terms": ["防蓝光"],
    },
    {
        "dim": "医院信息",
        "q": "眼科医院是哪家？",
        "answer": "市二院眼科",
        "terms": ["市二院"],
    },
    {
        "dim": "眼镜护理",
        "q": "眼镜怎么清洗？",
        "answer": "用洗镜液，不用纸巾",
        "terms": ["洗镜液"],
    },
    {
        "dim": "医生叮嘱",
        "q": "医生叮嘱什么？",
        "answer": "少看手机，多望远",
        "terms": ["望远"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="配镜视力",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="vision_mem0db",
        out_name="vision_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
