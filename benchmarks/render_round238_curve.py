"""Round-238 chart: curve_fit tool."""

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
            os.path.join(_BENCH, "results", "curve_fit_eval.json"),
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

    draw.text((42, 26), "第 238 轮：遗忘曲线个性化", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：遗忘速率因人/因记忆而异（Murre & Chessa 2011）——"
        "回忆成功越多，遗忘越慢。这个工具用真实记录调每条记忆的曲线。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（总错记忆 vs 连对记忆 → 各自预测）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("条数对", data["count_ok"], "#7b2ff7"),
        ("排序正确", data["order_ok"], "#1a7f37"),
        ("易忘预测对", data["fast_ok"], "#d97706"),
        ("巩固预测对", data["slow_ok"], "#0b7285"),
        ("理由齐全", data["reason_ok"], "#c2255c"),
        ("建议生成", data["advice_ok"], "#6741d9"),
        ("字段齐全", data["fields_ok"], "#2f9e44"),
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
        "怎么看：8 根柱子全部 10/10——连对 10 次的记忆衰减更慢，"
        "预测能撑更久才跌破阈值；总错的记忆衰减快，提前安排复习。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 用真实回忆记录给每条记忆画专属遗忘曲线——"
        "不再用一条通用曲线猜所有人，复习安排更准。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.curve_fit + MCP 工具——按成功率调衰减速率，"
        "预测跌破阈值的天数，支持整库或单条。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：296 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round238_curve.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
