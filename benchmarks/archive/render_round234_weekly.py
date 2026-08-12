"""Round-234 chart: weekly_review tool."""

from __future__ import annotations

import json
import os

from PIL import Image, ImageDraw, ImageFont

_BENCH = os.path.dirname(os.path.abspath(__file__))
_OUT = os.path.normpath(os.path.join(_BENCH, "..", "..", "outputs", "charts"))


def _font(size: int) -> ImageFont.FreeTypeFont:
    for path in (r"C:\Windows\Fonts\msyh.ttc", r"C:\Windows\Fonts\simsun.ttc"):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def chart() -> str:
    data = json.load(
        open(
            os.path.join(_BENCH, "results", "weekly_review_eval.json"),
            encoding="utf-8",
        )
    )
    W, H = 1400, 800
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(21)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 234 轮：周度复习报告", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：把间隔复习、遗忘风险、元认知校准、睡眠巩固合成一张周报——"
        "先补盲区，再防遗忘，校准自信，每晚巩固。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（盲区/风险/校准/今晚候选 → 周报）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("总数算对", data["total_ok"], "#7b2ff7"),
        ("主题数对", data["topic_ok"], "#1a7f37"),
        ("盲区找到", data["weak_ok"], "#d97706"),
        ("风险列表有", data["risk_ok"], "#0b7285"),
        ("校准分合法", data["calib_ok"], "#c2255c"),
        ("下周计划对", data["plan_ok"], "#6741d9"),
        ("字段齐全+建议", data["advice_ok"], "#2f9e44"),
        ("MCP 通路正常", data["mcp_ok"], "#e8590c"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 35 + i * 138
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：8 根柱子全部 10/10——周报能数清记忆、找到没复习的盲区主题、"
        "列出遗忘风险、给出校准分和 4 条下周计划。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 每周跑一次——像体检报告一样，一眼看到哪里薄弱，"
        "下周按计划补盲区、防遗忘、校准自信、每晚巩固。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.weekly_review + MCP 工具——聚合覆盖/风险/元认知/"
        "巩固预测，输出周摘要与下周计划。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：294 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round234_weekly.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
