"""Round-58 chart: interleaved vs blocked vs no practice."""

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
        open(os.path.join(_BENCH, "results", "interleave_eval.json"),
             encoding="utf-8")
    )
    inter = data["interleaved"]
    block = data["blocked"]
    none = data["none"]
    W, H = 1500, 1020
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    f_title = _font(30)
    f_sub = _font(18)
    f_panel = _font(22)
    f_label = _font(18)
    f_val = _font(17)
    f_note = _font(16)

    draw.text((42, 28), "第 58 轮：交错练习 vs 集中练习 vs 不复习",
              fill="#111", font=f_title)
    draw.text((42, 78),
              "依据：Rohrer & Taylor (2007) 交错练习——同类题目打散混排，"
              "避免连续刷同一类，帮助辨别相似记忆。",
              fill="#555", font=f_sub)

    # Panel 1: same-category adjacent rate (lower = better)
    x0 = 110
    base_y = 440
    chart_h = 260
    draw.text((x0, 140), "① 相邻两张卡是同类卡的比例（越低越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0%"), (0.1, "10%"), (0.2, "20%")):
        y = base_y - frac / 0.2 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 10), label, fill="#666", font=f_val)
    rows = [
        ("交错练习", inter["same_cat_ratio"], "#7b2ff7"),
        ("集中练习", block["same_cat_ratio"], "#b0b0b0"),
    ]
    for i, (name, val, color) in enumerate(rows):
        bx = x0 + 70 + i * 190
        bh = val / 0.2 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 130, base_y], fill=color)
        draw.text((bx + 42, base_y - bh + 8), f"{val:.1%}",
                  fill="white", font=f_val)
        draw.text((bx + 2, base_y + 12), name, fill="#111", font=f_label)

    # Panel 2: mean retrievability
    x0 = 820
    draw.text((x0, 140), "② 14 天后平均记住强度（越高越好）",
              fill="#111", font=f_panel)
    draw.line([(x0, base_y), (x0 + 560, base_y)], fill="#999", width=2)
    for frac, label in ((0.0, "0"), (0.3, "0.3"), (0.6, "0.6")):
        y = base_y - frac / 0.6 * chart_h
        draw.line([(x0, y), (x0 + 560, y)], fill="#e5e5e5", width=1)
        draw.text((x0 - 42, y - 10), label, fill="#666", font=f_val)
    rows2 = [
        ("交错练习", inter["mean_retrievability"], "#7b2ff7"),
        ("集中练习", block["mean_retrievability"], "#b0b0b0"),
        ("不复习", none["mean_retrievability"], "#d97706"),
    ]
    for i, (name, val, color) in enumerate(rows2):
        bx = x0 + 40 + i * 160
        bh = val / 0.6 * chart_h
        draw.rectangle([bx, base_y - bh, bx + 110, base_y], fill=color)
        draw.text((bx + 36, base_y - bh + 8), f"{val:.3f}",
                  fill="white", font=f_val)
        draw.text((bx - 8, base_y + 12), name, fill="#111", font=f_label)

    # Retained counts
    draw.text((42, 620), "③ 14 天后还记住多少条（共 30 条）",
              fill="#111", font=f_panel)
    rrows = [
        ("交错练习", inter["retained"], "#7b2ff7"),
        ("集中练习", block["retained"], "#b0b0b0"),
        ("不复习", none["retained"], "#d97706"),
    ]
    base_y2 = 850
    for i, (name, val, color) in enumerate(rrows):
        bx = 110 + i * 420
        bh = val / 30 * 190
        draw.rectangle([bx, base_y2 - bh, bx + 260, base_y2], fill=color)
        draw.text((bx + 110, base_y2 - bh + 8), f"{val}/30",
                  fill="white", font=f_val)
        draw.text((bx + 60, base_y2 + 12), name, fill="#111", font=f_label)

    draw.text((42, 910),
              "怎么看：交错练习把“连续刷同类卡”从 17.6% 降到 11.8%，"
              "记住强度与集中练习持平（0.624 vs 0.625），远好于不复习"
              "（0.292，只剩 13 条）——混排没有牺牲记忆，还练了辨别能力。",
              fill="#555", font=f_note)
    draw.text((42, 960),
              "实现：practice_due 新增 interleave（默认开），按卡片第一类提示词分桶"
              "、相邻卡不重复同类；已接入 MCP。回归：180 测试全过，88/200/10k 零差异。",
              fill="#555", font=f_note)

    path = os.path.join(_OUT, "round58_interleaving.png")
    img.save(path)
    return path


def main() -> int:
    os.makedirs(_OUT, exist_ok=True)
    print("written:", chart())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
