"""Round-61 chart: generation effect (own-phrase recall beats verbatim)."""

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
        open(os.path.join(_BENCH, "results", "generation_effect_eval.json"),
             encoding="utf-8")
    )
    W, H = 1450, 900
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(17)
    f_val = _font(16)
    f_note = _font(16)

    draw.text((42, 26), "第 61 轮：自己组织语言回忆，比照抄原文记得更牢",
              fill="#111", font=f_title)
    draw.text((42, 74),
              "依据：Slamecka & Graf (1978) 生成效应——生成（说出自己的话）比"
              "被动阅读/照抄产生更强的记忆。",
              fill="#555", font=f_sub)

    rows = [
        ("自己组织(新)", data["generated"]["mean_retrievability"],
         data["generated"]["per_review_gain"], data["generated"]["retained"],
         "#7b2ff7"),
        ("照抄原文", data["verbatim"]["mean_retrievability"],
         data["verbatim"]["per_review_gain"], data["verbatim"]["retained"],
         "#9ecbff"),
        ("重读", data["restudy"]["mean_retrievability"],
         data["restudy"]["per_review_gain"], data["restudy"]["retained"],
         "#b0b0b0"),
        ("不复习", data["none"]["mean_retrievability"],
         data["none"]["per_review_gain"], data["none"]["retained"],
         "#d97706"),
    ]

    # Panel 1: mean retrievability
    x0 = 90
    base_y = 390
    chart_h = 230
    draw.text((x0, 120), "① 2 周后的平均记住强度（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 540, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.3, "0.3"), (0.6, "0.6")):
        y = base_y - frac / 0.8 * chart_h
        draw.line([(x0, y), (x0 + 540, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 38, y - 9), label, fill="#666", font=f_val)
    for i, (name, val, _, _, color) in enumerate(rows):
        bx = x0 + 20 + i * 130
        bh = val / 0.8 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 105, base_y], fill=color)
        draw.text((bx + 32, base_y - bh + 6), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 18, base_y + 10), name, fill="#111", font=f_label)

    # Panel 2: per-review gain
    x0 = 760
    draw.text((x0, 120), "② 每次练习的净增益（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 540, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.004, "0.004"), (0.008, "0.008")):
        y = base_y - frac / 0.01 * chart_h
        draw.line([(x0, y), (x0 + 540, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 9), label, fill="#666", font=f_val)
    for i, (name, _, gain, _, color) in enumerate(rows):
        bx = x0 + 20 + i * 130
        bh = gain / 0.01 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 105, base_y], fill=color)
        draw.text((bx + 28, base_y - bh + 6), f"{gain:.5f}",
                  fill="white", font=f_val)
        draw.text((bx - 18, base_y + 10), name, fill="#111", font=f_label)

    draw.text((42, 610), "③ 2 周后还记住多少条（共 30 条）",
              fill="#111", font=f_panel)
    base_y2 = 830
    for i, (name, _, _, retained, color) in enumerate(rows):
        bx = 90 + i * 340
        bh = retained / 30 * 170
        draw.rectangle([bx, base_y2 - bh, bx + 240, base_y2], fill=color)
        draw.text((bx + 100, base_y2 - bh + 8), f"{retained}/30",
                  fill="white", font=f_val)
        draw.text((bx + 55, base_y2 + 10), name, fill="#111", font=f_label)

    draw.text((42, 950),
              "怎么看：自己组织语言的回忆（0.645）> 照抄原文（0.637）> 重读"
              "（0.586）> 不复习（0.292）；三种复习都能全记住 30 条，但生成"
              "每条练得更扎实。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round61_generation_effect.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
