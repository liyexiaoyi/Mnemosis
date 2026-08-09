"""Wedding-planning spot-check (round 274): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年2月14日求婚成功。",
        "kind": "episodic",
        "cues": ["2026-02-14", "求婚"],
    },
    {
        "content": "2026年3月1日定婚期：10 月 2 日。",
        "kind": "episodic",
        "cues": ["2026-03-01", "婚期"],
    },
    {
        "content": "2026年3月10日定酒店：凯悦厅，40 桌，每桌 3888 元。",
        "kind": "semantic",
        "cues": ["酒店", "凯悦厅"],
    },
    {
        "content": "2026年3月20日交酒店定金 2 万。",
        "kind": "episodic",
        "cues": ["2026-03-20", "定金"],
    },
    {
        "content": "2026年4月5日婚纱照预约：4 月 20 日拍摄。",
        "kind": "episodic",
        "cues": ["2026-04-05", "婚纱照"],
    },
    {
        "content": "2026年4月20日婚纱照拍完。",
        "kind": "episodic",
        "cues": ["2026-04-20", "婚纱照"],
    },
    {
        "content": "2026年5月1日定婚庆公司：司仪+布置 3.2 万。",
        "kind": "episodic",
        "cues": ["2026-05-01", "婚庆"],
    },
    {
        "content": "2026年5月15日选婚纱：主纱租赁 6800 元。",
        "kind": "episodic",
        "cues": ["2026-05-15", "主纱"],
    },
    {
        "content": "2026年6月1日发请柬：第一批 60 份。",
        "kind": "episodic",
        "cues": ["2026-06-01", "请柬"],
    },
    {
        "content": "2026年6月10日宾客统计：已确认 120 人。",
        "kind": "episodic",
        "cues": ["2026-06-10", "宾客"],
    },
    {
        "content": "2026年6月25日婚戒定制：8 月 10 日取。",
        "kind": "episodic",
        "cues": ["2026-06-25", "婚戒"],
    },
    {
        "content": "2026年7月5日预约 7 月 20 日试妆。",
        "kind": "episodic",
        "cues": ["2026-07-05", "试妆"],
    },
    {
        "content": "2026年7月20日试妆完成，定妆。",
        "kind": "episodic",
        "cues": ["2026-07-20", "试妆"],
    },
    {
        "content": "2026年8月1日蜜月旅行定：9 月 28 日出发，马尔代夫。",
        "kind": "episodic",
        "cues": ["2026-08-01", "蜜月"],
    },
    {
        "content": "2026年8月3日婚车预约：10 月 2 日 6 辆。",
        "kind": "episodic",
        "cues": ["2026-08-03", "婚车"],
    },
    {
        "content": "2026年8月6日收到婚庆确认：8 月 25 日彩排。",
        "kind": "episodic",
        "cues": ["2026-08-06", "彩排"],
    },
    {
        "content": "2026年8月8日尾款计划：9 月 15 日前付清。",
        "kind": "episodic",
        "cues": ["2026-08-08", "尾款"],
    },
    {
        "content": "婚宴菜单：8 菜 2 汤 1 甜点。",
        "kind": "semantic",
        "cues": ["菜单"],
    },
    {
        "content": "伴郎伴娘：4 对，需统一服装。",
        "kind": "semantic",
        "cues": ["伴郎伴娘"],
    },
    {
        "content": "化妆师电话 138-0000-8888。",
        "kind": "semantic",
        "cues": ["化妆师", "电话"],
    },
    {
        "content": "摄影师：老周，双机位。",
        "kind": "semantic",
        "cues": ["摄影师"],
    },
    {
        "content": "2026年8月9日预约 8 月 30 日选片。",
        "kind": "episodic",
        "cues": ["2026-08-09", "选片"],
    },
    {
        "content": "彩礼流程：双方父母见面已定 8 月 22 日。",
        "kind": "episodic",
        "cues": ["彩礼", "见面"],
    },
    {
        "content": "回门时间：婚后第三天。",
        "kind": "semantic",
        "cues": ["回门"],
    },
    {
        "content": "酒店联系人：王经理 139-1111-2222。",
        "kind": "semantic",
        "cues": ["酒店", "联系人"],
    },
]


QUESTIONS = [
    {
        "dim": "婚期安排",
        "q": "婚期是哪天？",
        "answer": "10月2日",
        "terms": ["2"],
    },
    {
        "dim": "酒店信息",
        "q": "酒店订在哪？多少桌？每桌多少钱？",
        "answer": "凯悦厅，40桌，3888元",
        "terms": ["3888"],
    },
    {
        "dim": "婚纱照",
        "q": "婚纱照什么时候拍的？",
        "answer": "4月20日",
        "terms": ["20"],
    },
    {
        "dim": "婚纱租赁",
        "q": "主纱多少钱？",
        "answer": "6800元",
        "terms": ["6800"],
    },
    {
        "dim": "婚戒定制",
        "q": "婚戒什么时候取？",
        "answer": "8月10日",
        "terms": ["10"],
    },
    {
        "dim": "蜜月安排",
        "q": "蜜月去哪？什么时候出发？",
        "answer": "马尔代夫，9月28日",
        "terms": ["马尔代夫"],
    },
    {
        "dim": "彩排安排",
        "q": "彩排是什么时候？",
        "answer": "8月25日",
        "terms": ["25"],
    },
    {
        "dim": "尾款计划",
        "q": "尾款什么时候付清？",
        "answer": "9月15日前",
        "terms": ["15"],
    },
    {
        "dim": "化妆师",
        "q": "化妆师电话多少？",
        "answer": "138-0000-8888",
        "terms": ["8888"],
    },
    {
        "dim": "彩礼流程",
        "q": "双方父母什么时候见面？",
        "answer": "8月22日",
        "terms": ["22"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="婚礼筹备",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="wedding_mem0db",
        out_name="wedding_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
