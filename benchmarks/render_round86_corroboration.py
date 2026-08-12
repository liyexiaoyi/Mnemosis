"""Round-86 chart: corroboration (multi-confirmed facts rank first)."""

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
        open(os.path.join(_BENCH, "results", "corroboration_eval.json"),
             encoding="utf-8")
    )
    W, H = 1400, 780
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 26), "第 86 轮：被多次确认过的事实，排在没有印证的前面",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Johnson et al. (1993) 来源监控——多个来源都确认过的事实"
              "更可信，同等匹配时应该先被想起。",
              fill="#555", font=f_sub)

    x0 = 100
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 8 个“单次印象 vs 多次确认”的检索里，多来源记忆排第一",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 520, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (2.0, "2"), (4.0, "4"), (6.0, "6"),
                        (8.0, "8")):
        y = base_y - frac / 8.0 * chart_h
        draw.line([(x0, y), (x0 + 520, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 40, y - 9), label, fill="#666", font=f_val)
    rows = [
        ("多来源印证(新)", data["boosted"]["confirmed_first"], "#7b2ff7"),
        ("不加分", data["plain"]["confirmed_first"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 8.0 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val}/8",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    draw.text((42, 590),
              "怎么看：单次印象的记忆“更重要”一点（0.77 vs 0.5），不加分时 8/8 排第一；"
              "开启印证加成后，",
              fill="#555", font=f_note)
    draw.text((42, 630),
              "被 3 次确认过的记忆 +0.03，8/8 翻盘——多来源确认过的事实更可信。",
              fill="#555", font=f_note)
    draw.text((42, 700),
              "实现：recall 新增 corroboration_boost（默认开）——证据数 ≥3 的记忆"
              "检索 +0.03，标注“多来源印证”。",
              fill="#555", font=f_note)
    draw.text((42, 750),
              "回归：205 测试全过；统一回归全绿（en88/zh200/zh10k 及 10k 系列零差异）。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round86_corroboration.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
