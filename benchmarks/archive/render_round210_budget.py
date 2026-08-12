"""Round-210 chart: working_set_budget tool."""

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
            os.path.join(_BENCH, "results", "working_set_budget_eval.json"),
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

    draw.text((42, 26), "第 210 轮：工作记忆预算", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：工作记忆容量约 7±2 个组块（Miller 1956）、焦点 4±1（Cowan 2001）；"
        "认知负荷过大伤学习（Sweller 1988）——这个工具看当前工作集装不装得下。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 组 ×（9 条大负载 + 3 条小负载）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("大负载数对", data["big_count_ok"], "#7b2ff7"),
        ("超载判断对", data["verdict_ok"], "#1a7f37"),
        ("负载比例对", data["ratio_ok"], "#d97706"),
        ("按主题分块对", data["chunk_ok"], "#0b7285"),
        ("分批建议对", data["advice_ok"], "#c2255c"),
        ("小负载判断对", data["small_ok"], "#6741d9"),
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
        "怎么看：8 根柱子全部 10/10——9 条记忆时判定“超载”并按主题分块，"
        "3 条记忆时判定“没装满”，不会把工作区塞爆。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 组织上下文前跑一次——超载就按主题分批、每批不超过 4 条，"
        "像人一样一次专注一个主题，学得更牢、计划更清楚。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.working_set_budget + MCP 工具——比对工作集与容量，"
        "按主题分块并给负载判定与建议。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：280 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round210_budget.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
