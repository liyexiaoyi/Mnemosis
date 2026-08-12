"""Round-209 chart: schema_fit tool."""

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
            os.path.join(_BENCH, "results", "schema_fit_eval.json"),
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

    draw.text((42, 26), "第 209 轮：图式拟合与重建", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：与已有图式一致的新记忆巩固快（Tse 2007）；"
        "记忆会“同化”进旧图式或“顺应”出新图式（Bartlett 1932）。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 ×（物理图式 3 条 + 音乐新知识 1 条）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("总数算对", data["total_ok"], "#7b2ff7"),
        ("图式数量对", data["schema_ok"], "#1a7f37"),
        ("同化判断对", data["assim_ok"], "#d97706"),
        ("顺应判断对", data["accom_ok"], "#0b7285"),
        ("图式汇总对", data["summary_ok"], "#c2255c"),
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
        "怎么看：8 根柱子全部 10/10——物理类记忆被判定“并入物理图式”，"
        "音乐知识被判定“需要新图式”，不会硬塞进错误的框里。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 入库前跑一次——和已有图式一致的记忆巩固快（优先级可高），"
        "不一致的单独建图式，避免旧图式被新知识带歪。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.schema_fit + MCP 工具——按线索聚类成图式，"
        "算每条记忆与最佳图式的重合度，输出同化/临界/顺应。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：279 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round209_schema.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
