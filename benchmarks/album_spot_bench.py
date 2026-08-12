"""Family-album spot-check (round 304): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot

DATASET = [
    {
        "content": "2026年1月10日建家庭相册。",
        "kind": "episodic",
        "cues": ["2026-01-10", "相册"],
    },
    {
        "content": "2026年1月20日导入手机照片 2000 张。",
        "kind": "episodic",
        "cues": ["2026-01-20", "导入"],
    },
    {
        "content": "2026年2月1日分类：旅行、美食、家人。",
        "kind": "semantic",
        "cues": ["分类"],
    },
    {
        "content": "2026年2月15日备份到云盘。",
        "kind": "episodic",
        "cues": ["2026-02-15", "备份"],
    },
    {
        "content": "2026年3月1日预约 3 月 10 日洗照片。",
        "kind": "episodic",
        "cues": ["2026-03-01", "洗照片"],
    },
    {
        "content": "2026年3月10日洗照片 120 张。",
        "kind": "episodic",
        "cues": ["2026-03-10", "洗照片"],
    },
    {
        "content": "2026年4月1日买相册本。",
        "kind": "episodic",
        "cues": ["2026-04-01", "相册本"],
    },
    {
        "content": "2026年4月15日贴照片完成。",
        "kind": "episodic",
        "cues": ["2026-04-15", "贴照片"],
    },
    {
        "content": "2026年5月1日制作电子相册。",
        "kind": "episodic",
        "cues": ["2026-05-01", "电子相册"],
    },
    {
        "content": "2026年5月20日预约 6 月 1 日照片修复。",
        "kind": "episodic",
        "cues": ["2026-05-20", "修复"],
    },
    {
        "content": "2026年6月1日修复老照片完成。",
        "kind": "episodic",
        "cues": ["2026-06-01", "修复"],
    },
    {
        "content": "2026年7月1日整理视频。",
        "kind": "episodic",
        "cues": ["2026-07-01", "视频"],
    },
    {
        "content": "2026年7月15日预约 7 月 25 日摄影棚拍全家福。",
        "kind": "episodic",
        "cues": ["2026-07-15", "全家福"],
    },
    {
        "content": "2026年7月25日全家福拍完。",
        "kind": "episodic",
        "cues": ["2026-07-25", "全家福"],
    },
    {
        "content": "2026年8月1日预约 8 月 12 日选照片。",
        "kind": "episodic",
        "cues": ["2026-08-01", "选照片"],
    },
    {
        "content": "2026年8月5日收到提醒：8 月 15 日云盘容量不足。",
        "kind": "episodic",
        "cues": ["2026-08-05", "云盘"],
    },
    {
        "content": "摄影店电话 400-123-9999。",
        "kind": "semantic",
        "cues": ["摄影店", "电话"],
    },
    {
        "content": "相册本分类：按年份。",
        "kind": "semantic",
        "cues": ["相册本", "年份"],
    },
    {
        "content": "2026年8月8日收到通知：8 月 20 日摄影展。",
        "kind": "episodic",
        "cues": ["2026-08-08", "摄影展"],
    },
]


QUESTIONS = [
    {
        "dim": "照片分类",
        "q": "照片怎么分类？",
        "answer": "旅行、美食、家人",
        "terms": ["美食"],
    },
    {
        "dim": "导入数量",
        "q": "导入了多少张照片？",
        "answer": "2000张",
        "terms": ["2000"],
    },
    {
        "dim": "洗照片",
        "q": "洗了多少张照片？",
        "answer": "120张",
        "terms": ["120"],
    },
    {
        "dim": "未来安排",
        "q": "下次选照片是什么时候？",
        "answer": "8月12日",
        "terms": ["12"],
    },
    {
        "dim": "照片修复",
        "q": "老照片什么时候修复的？",
        "answer": "6月1日",
        "terms": ["1"],
    },
    {
        "dim": "全家福",
        "q": "全家福什么时候拍的？",
        "answer": "7月25日",
        "terms": ["25"],
    },
    {
        "dim": "照片备份",
        "q": "照片备份到哪？",
        "answer": "云盘",
        "terms": ["云盘"],
    },
    {
        "dim": "摄影店",
        "q": "摄影店电话多少？",
        "answer": "400-123-9999",
        "terms": ["9999"],
    },
    {
        "dim": "相册分类",
        "q": "相册本怎么分类？",
        "answer": "按年份",
        "terms": ["年份"],
    },
    {
        "dim": "摄影展",
        "q": "摄影展什么时候？",
        "answer": "8月20日",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="家庭相册",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="album_mem0db",
        out_name="album_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
