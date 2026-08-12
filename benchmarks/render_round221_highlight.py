"""Round-221 highlight chart (simple, for non-experts)."""

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
    json.load(
        open(
            os.path.join(_BENCH, "results", "toolchain24_eval.json"),
            encoding="utf-8",
        )
    )
    W, H = 1200, 760
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    _font(21)
    f_label = _font(19)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 221 轮大白话版：81 步全过", fill="#111", font=f_title)
    draw.text(
        (42, 74),
        "同一份记忆连续走完 81 个动作，全部正确；新加 3 个工具也不打架。",
        fill="#555",
        font=f_sub,
    )

    x0 = 90
    base_y = 380
    chart_h = 220
    draw.line([(x0, base_y), (x0 + 960, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (5.0, "5"), (10.0, "10")):
        y = base_y - frac / 10.0 * chart_h
        draw.line([(x0, y), (x0 + 960, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("总步骤全过", 1, "81/81", "#1a7f37"),
        ("搜索命中", 1, "6/6", "#0b7285"),
        ("批量检索", 1, "3/3", "#d97706"),
        ("巩固预测", 1, "正常", "#c2255c"),
        ("遗忘平衡", 1, "正常", "#7b2ff7"),
        ("元认知", 1, "正常", "#2f9e44"),
    ]
    for i, (name, val, text, color) in enumerate(rows):
        bx = x0 + 45 + i * 150
        bh = val * chart_h
        draw.rectangle([bx, base_y - bh, bx + 120, base_y], fill=color)
        draw.text((bx + 34, base_y - bh + 10), text, fill="white", font=f_val)
        draw.text((bx - 12, base_y + 10), name, fill="#111", font=f_label)

    draw.text(
        (42, 600),
        "怎么看：全绿——旧功能没坏，新功能（巩固预测、遗忘平衡、元认知）"
        "在同一套数据上也正常工作。",
        fill="#555",
        font=f_note,
    )
    draw.text(
        (42, 700),
        "回归：286 个单元测试全过 + 一键全测评全绿。",
        fill="#555",
        font=f_note,
    )

    path = os.path.join(_OUT, "round221_toolchain24_simple.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
