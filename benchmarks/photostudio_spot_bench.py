"""Kids-photo-studio spot-check (round 347): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月6日第一次预约儿童摄影，周岁套餐1999元。",
        "kind": "episodic",
        "cues": ["2026-01-06", "摄影"],
    },
    {
        "content": "2026年1月20日第一次拍摄完成。",
        "kind": "episodic",
        "cues": ["2026-01-20", "拍摄"],
    },
    {
        "content": "影楼营业时间：早9点到晚6点。",
        "kind": "semantic",
        "cues": ["营业时间", "9点"],
    },
    {
        "content": "影楼电话 0532-7777-5555。",
        "kind": "semantic",
        "cues": ["电话"],
    },
    {
        "content": "拍摄项目：周岁照、亲子照、外景照、证件照。",
        "kind": "semantic",
        "cues": ["项目", "周岁照"],
    },
    {
        "content": "2026年2月2日预约2月15日选片。",
        "kind": "episodic",
        "cues": ["2026-02-02", "选片"],
    },
    {
        "content": "2026年2月15日选片完成，精修20张。",
        "kind": "episodic",
        "cues": ["2026-02-15", "选片"],
    },
    {
        "content": "服装道具：提供3套服装和头饰。",
        "kind": "semantic",
        "cues": ["服装", "道具"],
    },
    {
        "content": "2026年3月8日收到通知：3月22日相册制作完成。",
        "kind": "episodic",
        "cues": ["2026-03-08", "相册"],
    },
    {
        "content": "2026年3月22日取回相册。",
        "kind": "episodic",
        "cues": ["2026-03-22", "相册"],
    },
    {
        "content": "2026年4月10日收到通知：4月25日春季外景拍摄。",
        "kind": "episodic",
        "cues": ["2026-04-10", "外景"],
    },
    {
        "content": "2026年4月25日外景拍摄完成。",
        "kind": "episodic",
        "cues": ["2026-04-25", "外景"],
    },
    {
        "content": "2026年5月15日预约5月28日亲子照拍摄。",
        "kind": "episodic",
        "cues": ["2026-05-15", "亲子照"],
    },
    {
        "content": "2026年5月28日亲子照完成。",
        "kind": "episodic",
        "cues": ["2026-05-28", "亲子照"],
    },
    {
        "content": "2026年6月10日收到通知：6月25日暑期套餐优惠。",
        "kind": "episodic",
        "cues": ["2026-06-10", "优惠"],
    },
    {
        "content": "2026年6月25日暑期套餐优惠开始。",
        "kind": "episodic",
        "cues": ["2026-06-25", "优惠"],
    },
    {
        "content": "2026年7月8日预约7月22日证件照拍摄。",
        "kind": "episodic",
        "cues": ["2026-07-08", "证件照"],
    },
    {
        "content": "2026年7月22日证件照完成。",
        "kind": "episodic",
        "cues": ["2026-07-22", "证件照"],
    },
    {
        "content": "2026年8月2日预约8月16日下次拍摄。",
        "kind": "episodic",
        "cues": ["2026-08-02", "拍摄"],
    },
    {
        "content": "2026年8月10日收到提醒：8月25日底片领取截止。",
        "kind": "episodic",
        "cues": ["2026-08-10", "底片"],
    },
]


QUESTIONS = [
    {
        "dim": "首次预约",
        "q": "第一次预约儿童摄影是什么时候？",
        "answer": "1月6日",
        "terms": ["6"],
    },
    {
        "dim": "套餐价格",
        "q": "周岁套餐多少钱？",
        "answer": "1999元",
        "terms": ["1999"],
    },
    {
        "dim": "下次拍摄",
        "q": "下次拍摄是什么时候？",
        "answer": "8月16日",
        "terms": ["16"],
    },
    {
        "dim": "营业时间",
        "q": "影楼几点开门？",
        "answer": "早9点",
        "terms": ["9"],
    },
    {
        "dim": "电话",
        "q": "影楼电话多少？",
        "answer": "0532-7777-5555",
        "terms": ["5555"],
    },
    {
        "dim": "拍摄项目",
        "q": "影楼有哪些拍摄项目？",
        "answer": "周岁照、亲子照、外景照、证件照",
        "terms": ["亲子照"],
    },
    {
        "dim": "精修数量",
        "q": "精修多少张照片？",
        "answer": "20张",
        "terms": ["20"],
    },
    {
        "dim": "服装道具",
        "q": "影楼提供几套服装？",
        "answer": "3套",
        "terms": ["3"],
    },
    {
        "dim": "相册",
        "q": "相册什么时候取回的？",
        "answer": "3月22日",
        "terms": ["22"],
    },
    {
        "dim": "底片领取",
        "q": "底片领取什么时候截止？",
        "answer": "8月25日",
        "terms": ["25"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="儿童摄影",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="photostudio_mem0db",
        out_name="photostudio_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
