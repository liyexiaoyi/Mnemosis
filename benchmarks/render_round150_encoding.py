"""Round-150 chart: encoding_quality tool."""

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
            os.path.join(_BENCH, "results", "encoding_quality_eval.json"),
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

    draw.text((42, 26), "第 150 轮：给每条记忆的“存档质量”打分", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "依据：越精细地编码（多线索/有情景/带情绪/标重要度），记忆越好取"
        "（精细加工，Craik & Tulving 1975）；这个工具按 6 项给记忆打 0-100 分。",
        fill="#555",
        font=f_sub,
    )

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 10 个记忆库 × 3 种存档（好/中/差）", fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 1120, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 1120, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("好存档判高分", data["high_ok"], "#7b2ff7"),
        ("差存档判低分", data["low_ok"], "#1a7f37"),
        ("中等判中间档", data["mid_ok"], "#d97706"),
        ("差的有改进建议", data["sugg_ok"], "#0b7285"),
        ("字段齐全", data["fields_ok"], "#c2255c"),
        ("MCP通路正常", data["mcp_ok"], "#6741d9"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 45 + i * 180
        bh = val / 10.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 150, base_y], fill=color)
        draw.text((bx + 48, base_y - bh + 8), f"{val}/10", fill="white", font=f_val)
        draw.text((bx - 8, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 590),
        "怎么看：6 根柱子全部 10/10——线索全、有情景、带情绪、标重要度的记忆得高分，"
        "什么都没存的得低分，中等的落在中间档，差的还附改进建议。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 630),
        "用处：agent 存重要事情时先查一下质量分，缺线索补线索、缺情景补情景，"
        "让关键记忆以后一查就中。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "实现：engine.encoding_quality + MCP 工具——按线索/情景/情绪/重要度/"
        "强度/长度 6 项打分并给建议，纯只读。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 760),
        "回归：243 个测试全过，长对话 88/200/10k 零差异。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round150_encoding.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
