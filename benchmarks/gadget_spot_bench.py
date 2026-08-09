"""Gadgets & warranties spot-check (round 276): Mnemosis vs mem0 ONLY."""

from __future__ import annotations

import argparse

from spot_common import run_spot


DATASET = [
    {
        "content": "2026年1月10日买笔记本：联想拯救者，8599 元，保修 2 年。",
        "kind": "semantic",
        "cues": ["笔记本", "8599"],
    },
    {
        "content": "2026年1月20日买显示器：2K 27 寸，1499 元。",
        "kind": "episodic",
        "cues": ["2026-01-20", "显示器"],
    },
    {
        "content": "2026年2月1日笔记本蓝屏，2 月 3 日重装系统。",
        "kind": "episodic",
        "cues": ["2026-02-01", "蓝屏"],
    },
    {
        "content": "2026年2月15日买机械键盘 399 元。",
        "kind": "episodic",
        "cues": ["2026-02-15", "键盘"],
    },
    {
        "content": "2026年3月1日键盘按键失灵，3 月 5 日售后换新。",
        "kind": "episodic",
        "cues": ["2026-03-01", "换新"],
    },
    {
        "content": "2026年3月10日收到换新键盘。",
        "kind": "episodic",
        "cues": ["2026-03-10", "换新"],
    },
    {
        "content": "2026年4月1日买路由器：WiFi6，329 元。",
        "kind": "episodic",
        "cues": ["2026-04-01", "路由器"],
    },
    {
        "content": "2026年4月15日路由器信号差，4 月 18 日调位置。",
        "kind": "episodic",
        "cues": ["2026-04-15", "路由器"],
    },
    {
        "content": "2026年5月1日买平板：iPad，3499 元，AC+ 一年。",
        "kind": "semantic",
        "cues": ["平板", "AC+"],
    },
    {
        "content": "2026年5月20日平板屏幕划痕，贴膜。",
        "kind": "episodic",
        "cues": ["2026-05-20", "平板"],
    },
    {
        "content": "2026年6月1日手机电池鼓包，6 月 5 日换电池 399 元。",
        "kind": "episodic",
        "cues": ["2026-06-01", "电池"],
    },
    {
        "content": "2026年6月20日耳机丢失，重买 599 元。",
        "kind": "episodic",
        "cues": ["2026-06-20", "耳机"],
    },
    {
        "content": "2026年7月1日显示器闪烁，预约 7 月 10 日上门检测。",
        "kind": "episodic",
        "cues": ["2026-07-01", "显示器"],
    },
    {
        "content": "2026年7月10日显示器检测：换排线。",
        "kind": "episodic",
        "cues": ["2026-07-10", "排线"],
    },
    {
        "content": "2026年7月25日买 NAS：群晖 2 盘位，2600 元。",
        "kind": "episodic",
        "cues": ["2026-07-25", "NAS"],
    },
    {
        "content": "2026年8月1日 NAS 配置完成。",
        "kind": "episodic",
        "cues": ["2026-08-01", "NAS"],
    },
    {
        "content": "2026年8月5日预约 8 月 15 日数据迁移。",
        "kind": "episodic",
        "cues": ["2026-08-05", "迁移"],
    },
    {
        "content": "保修记录：笔记本发票放抽屉。",
        "kind": "semantic",
        "cues": ["保修", "发票"],
    },
    {
        "content": "设备清单：键盘型号 K87，鼠标 G304。",
        "kind": "semantic",
        "cues": ["键盘", "K87"],
    },
    {
        "content": "2026年8月8日收到提醒：8 月 20 日平板 AC+ 到期前检查。",
        "kind": "episodic",
        "cues": ["2026-08-08", "AC+"],
    },
    {
        "content": "路由器密码 admin888。",
        "kind": "semantic",
        "cues": ["路由器", "密码"],
    },
    {
        "content": "云盘：主力用阿里云盘 2TB。",
        "kind": "semantic",
        "cues": ["云盘", "阿里"],
    },
    {
        "content": "2026年8月9日预约 8 月 18 日硬盘加装。",
        "kind": "episodic",
        "cues": ["2026-08-09", "硬盘"],
    },
]


QUESTIONS = [
    {
        "dim": "设备信息",
        "q": "笔记本多少钱？保修多久？",
        "answer": "8599元，2年",
        "terms": ["8599"],
    },
    {
        "dim": "维修记录",
        "q": "上次维修是什么时候？修的什么？",
        "answer": "7月10日，显示器换排线",
        "terms": ["排线"],
    },
    {
        "dim": "换新记录",
        "q": "上次换新是什么时候？",
        "answer": "3月5日键盘售后换新",
        "terms": ["5"],
    },
    {
        "dim": "未来安排",
        "q": "下次数据迁移是什么时候？",
        "answer": "8月15日",
        "terms": ["15"],
    },
    {
        "dim": "手机维修",
        "q": "手机电池怎么了？换电池多少钱？",
        "answer": "鼓包，399元",
        "terms": ["399"],
    },
    {
        "dim": "路由器",
        "q": "路由器什么问题？怎么解决的？",
        "answer": "信号差，调位置",
        "terms": ["信号"],
    },
    {
        "dim": "平板保修",
        "q": "平板有保修吗？",
        "answer": "AC+一年",
        "terms": ["AC"],
    },
    {
        "dim": "路由器密码",
        "q": "路由器密码多少？",
        "answer": "admin888",
        "terms": ["admin"],
    },
    {
        "dim": "云盘",
        "q": "主力云盘是什么？多大？",
        "answer": "阿里云盘2TB",
        "terms": ["阿里"],
    },
    {
        "dim": "到期提醒",
        "q": "平板 AC+ 什么时候检查？",
        "answer": "8月20日前",
        "terms": ["20"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skip-answers", action="store_true")
    args = parser.parse_args()
    return run_spot(
        domain="电子设备",
        dataset=DATASET,
        questions=QUESTIONS,
        db_name="gadget_mem0db",
        out_name="gadget_spot.json",
        skip_answers=args.skip_answers,
    )


if __name__ == "__main__":
    raise SystemExit(main())
